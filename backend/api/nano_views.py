import json,logging,base64,os,requests
from datetime import datetime
from decimal import Decimal
from django.db.models import Q
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response
from .models import Escrow,WebhookLog
logger=logging.getLogger(__name__)
def _get_token():
    key=os.environ.get("MPESA_CONSUMER_KEY","");secret=os.environ.get("MPESA_CONSUMER_SECRET","")
    env=os.environ.get("MPESA_ENVIRONMENT","sandbox")
    base="https://sandbox.safaricom.co.ke" if env=="sandbox" else "https://api.safaricom.co.ke"
    creds=base64.b64encode(f"{key}:{secret}".encode()).decode()
    r=requests.get(f"{base}/oauth/v1/generate?grant_type=client_credentials",headers={"Authorization":f"Basic {creds}"},timeout=10)
    r.raise_for_status();return r.json()["access_token"],base
def _stk(phone,amount,deal_code):
    token,base=_get_token();sc=os.environ.get("MPESA_SHORTCODE","174379");pk=os.environ.get("MPESA_PASSKEY","");cb=os.environ.get("MPESA_CALLBACK_URL","")
    phone=phone.strip().lstrip("+")
    if phone.startswith("0"):phone="254"+phone[1:]
    if not phone.startswith("254"):phone="254"+phone
    ts=datetime.now().strftime("%Y%m%d%H%M%S");pwd=base64.b64encode(f"{sc}{pk}{ts}".encode()).decode()
    r=requests.post(f"{base}/mpesa/stkpush/v1/processrequest",json={"BusinessShortCode":sc,"Password":pwd,"Timestamp":ts,"TransactionType":"CustomerPayBillOnline","Amount":int(amount),"PartyA":phone,"PartyB":sc,"PhoneNumber":phone,"CallBackURL":cb,"AccountReference":deal_code[:12],"TransactionDesc":f"Pay {deal_code}"[:13]},headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"},timeout=15)
    return r.json()
def _d(e):
    return {"deal_code":e.deal_code,"sender":e.sender.username,"receiver":e.receiver.username if e.receiver else None,"amount":str(e.amount),"fee":str(e.fee),"fee_label":f"KES {e.fee} (1.5%)","total_payable":str(e.total_payable),"state":e.state,"mpesa_checkout_id":e.mpesa_checkout_id,"mpesa_receipt":e.mpesa_receipt,"description":e.description,"created_at":e.created_at.isoformat(),"updated_at":e.updated_at.isoformat()}
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def nano_create_deal(request):
    amt=request.data.get("amount")
    if not amt:return Response({"error":"amount required"},status=400)
    try:amt=Decimal(str(amt));assert amt>0
    except:return Response({"error":"amount must be positive"},status=400)
    rcv=None;rid=request.data.get("receiver_id")
    if rid:
        from django.contrib.auth.models import User
        try:rcv=User.objects.get(pk=rid)
        except:return Response({"error":"Receiver not found"},status=404)
    e=Escrow.objects.create(sender=request.user,receiver=rcv,amount=amt,description=request.data.get("description",""))
    return Response(_d(e),status=201)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def nano_pay(request):
    code=request.data.get("deal_code","").strip().upper();phone=request.data.get("phone","").strip()
    if not code or not phone:return Response({"error":"deal_code and phone required"},status=400)
    try:e=Escrow.objects.get(deal_code=code)
    except Escrow.DoesNotExist:return Response({"error":"Deal not found"},status=404)
    if e.state!=Escrow.STATE_PENDING:return Response({"error":f"Deal is {e.state}"},status=400)
    try:
        resp=_stk(phone,e.total_payable,code)
        if resp.get("ResponseCode")=="0":
            e.mpesa_checkout_id=resp.get("CheckoutRequestID");e.save(update_fields=["mpesa_checkout_id","updated_at"])
            return Response({"success":True,"message":"STK Push sent","deal_code":code,"amount_charged":str(e.total_payable)})
        return Response({"success":False,"message":resp.get("ResponseDescription","Failed")},status=400)
    except Exception as ex:return Response({"error":str(ex)},status=500)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def nano_deal_status(request,deal_code):
    try:e=Escrow.objects.get(deal_code=deal_code.upper())
    except Escrow.DoesNotExist:return Response({"error":"Deal not found"},status=404)
    return Response(_d(e))
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def nano_release(request,deal_code):
    try:e=Escrow.objects.get(deal_code=deal_code.upper())
    except Escrow.DoesNotExist:return Response({"error":"Deal not found"},status=404)
    if e.sender!=request.user and not request.user.is_staff:return Response({"error":"Only sender or admin"},status=403)
    try:
        if request.data.get("action")=="refund":e.mark_refunded();msg=f"Deal {deal_code} refunded"
        else:e.mark_done();msg=f"Deal {deal_code} released"
        return Response({"success":True,"message":msg,"state":e.state})
    except ValueError as ex:return Response({"error":str(ex)},status=400)
@api_view(["POST"])
@permission_classes([AllowAny])
def nano_mpesa_callback(request):
    try:
        raw=json.loads(request.body);stk=raw.get("Body",{}).get("stkCallback",{})
        rc=stk.get("ResultCode");cid=stk.get("CheckoutRequestID","");ref=stk.get("AccountReference","").upper()
        e=Escrow.objects.filter(Q(deal_code=ref)|Q(mpesa_checkout_id=cid)).first()
        event="stk_callback_success" if rc==0 else "stk_callback_failure"
        WebhookLog.objects.create(escrow=e,event=event,payload=raw)
        if rc==0:
            items=stk.get("CallbackMetadata",{}).get("Item",[])
            receipt=next((i["Value"] for i in items if i["Name"]=="MpesaReceiptNumber"),None)
            if e:
                try:e.mark_held(mpesa_checkout_id=cid,mpesa_receipt=receipt)
                except ValueError as ex:logger.warning(f"skip:{ex}")
        return Response({"ResultCode":0,"ResultDesc":"Success"})
    except Exception as ex:return Response({"ResultCode":1,"ResultDesc":"Error"})

class SMSService:
    @staticmethod
    def clean_phone(phone):
        phone = str(phone).strip().replace(' ', '').replace('-', '').lstrip('+')
        if phone.startswith('0'):
            phone = '254' + phone[1:]
        elif not phone.startswith('254'):
            phone = '254' + phone
        return phone

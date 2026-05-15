/**
 * TrustLayer SDK v1.0
 * Embed secure escrow payments on any website.
 *
 * Usage:
 *   <script src="https://yourdomain.com/static/js/sdk.js"></script>
 *   <script>
 *     TrustLayer.open({
 *       token: 'session_token_from_your_backend',
 *       onSuccess: function(data) { console.log('Payment held!', data); },
 *       onFailure: function(data) { console.log('Failed', data); },
 *       onCancel:  function()     { console.log('Cancelled'); }
 *     });
 *   </script>
 */
(function (window) {
  var modal = null;
  var iframe = null;
  var _callbacks = {};

  function buildModal() {
    if (modal) return;

    // Overlay
    modal = document.createElement('div');
    modal.id = 'tl-modal';
    modal.style.cssText = [
      'position:fixed;top:0;left:0;width:100%;height:100%;',
      'background:rgba(0,0,0,.65);display:none;',
      'justify-content:center;align-items:center;z-index:2147483647;',
      'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;'
    ].join('');

    // Card
    var card = document.createElement('div');
    card.style.cssText = [
      'background:#fff;border-radius:20px;width:92%;max-width:460px;',
      'max-height:92vh;overflow:hidden;',
      'box-shadow:0 24px 64px rgba(0,0,0,.35);display:flex;flex-direction:column;'
    ].join('');

    // Header
    var hdr = document.createElement('div');
    hdr.style.cssText = 'background:#0d1117;padding:16px 20px;display:flex;justify-content:space-between;align-items:center;flex-shrink:0;';
    hdr.innerHTML = [
      '<div style="display:flex;align-items:center;gap:8px;">',
      '  <span style="font-size:18px;">🛡️</span>',
      '  <span style="font-weight:700;color:#fff;font-size:15px;">TrustLayer</span>',
      '  <span style="background:#00c46a;color:#fff;font-size:10px;padding:2px 8px;border-radius:20px;letter-spacing:.04em;">SECURE ESCROW</span>',
      '</div>',
      '<button id="tl-close" style="background:none;border:none;color:#9ca3af;font-size:22px;cursor:pointer;line-height:1;">&#x2715;</button>'
    ].join('');

    // iFrame body
    var body = document.createElement('div');
    body.style.cssText = 'flex:1;overflow:hidden;';

    iframe = document.createElement('iframe');
    iframe.style.cssText = 'width:100%;height:100%;border:none;min-height:480px;';
    iframe.setAttribute('allow', 'payment');

    body.appendChild(iframe);
    card.appendChild(hdr);
    card.appendChild(body);
    modal.appendChild(card);
    document.body.appendChild(modal);

    // Close button
    hdr.querySelector('#tl-close').onclick = function () { _close('cancel'); };

    // Click outside
    modal.onclick = function (e) { if (e.target === modal) _close('cancel'); };

    // Listen for messages from iframe
    window.addEventListener('message', function (e) {
      if (!e.data || !e.data.type) return;
      if (e.data.type === 'tl-success') _close('success', e.data);
      if (e.data.type === 'tl-failure') _close('failure', e.data);
      if (e.data.type === 'tl-cancel')  _close('cancel');
    });
  }

  function _close(reason, data) {
    if (modal) modal.style.display = 'none';
    if (reason === 'success' && _callbacks.onSuccess) _callbacks.onSuccess(data || {});
    if (reason === 'failure' && _callbacks.onFailure) _callbacks.onFailure(data || {});
    if (reason === 'cancel'  && _callbacks.onCancel)  _callbacks.onCancel();
  }

  window.TrustLayer = {
    open: function (cfg) {
      buildModal();
      _callbacks = {
        onSuccess: cfg.onSuccess || null,
        onFailure: cfg.onFailure || null,
        onCancel:  cfg.onCancel  || null,
      };
      var base = cfg.baseUrl || window.location.origin;
      iframe.src = base + '/pay/' + cfg.token + '/?embed=1';
      modal.style.display = 'flex';
    },
    close: function () { _close('cancel'); }
  };

  console.log('[TrustLayer SDK] loaded. Call TrustLayer.open({ token: "..." }) to start.');
}(window));

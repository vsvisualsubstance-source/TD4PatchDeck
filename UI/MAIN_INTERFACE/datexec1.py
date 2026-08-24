def onTableChange(dat):
    led_ctrl = op('/PATCHDECK/CTRL/led_controller')
    if led_ctrl and led_ctrl.ext.PATCHDECKCTRLledcontroller1:
        led_ctrl.ext.PATCHDECKCTRLledcontroller1.refreshAll()
    return

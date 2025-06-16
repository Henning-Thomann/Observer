from tinkerforge.bricklet_nfc import BrickletNFC

class NfcReader:
    VALID_NFC_ID_SUFFIX = 0x90
    DOOM_NFC_SUFFIC = 0x80

    def __init__(self, conn, count_down, alarm):
        self._alarm = alarm
        self._count_down = count_down
        self._nfc = BrickletNFC("22ND", conn)
        self.doom_mode = False

    def setup(self):
        self._nfc.register_callback(self._nfc.CALLBACK_READER_STATE_CHANGED,
                            lambda x, y: self.cb_reader_state_changed(x, y, self._nfc))
        self._nfc.set_mode(self._nfc.MODE_READER)

    def cb_reader_state_changed(self, state, idle, nfc):
        if state == nfc.READER_STATE_REQUEST_TAG_ID_READY:
            ret = nfc.reader_get_tag_id()
            tag_id = list(ret.tag_id)

            print("Found tag of type " +
                str(ret.tag_type) +
                " with ID [" +
                " ".join(map(str, map('0x{:02X}'.format, ret.tag_id))) +
                "]")

            if tag_id[-1] == self.VALID_NFC_ID_SUFFIX:
                print("Valid NFC card scanned - Stopping countdown and disabling motion detection")
                self._count_down.stop_count_down()
                self._alarm.enable_reset()
                self._count_down.disable_motion_detection()  # Verwende die neue Methode!
            elif tag_id[-1] == self.DOOM_NFC_SUFFIC:
                self.doom_mode = True
            else:
                print("Scanned card doesn't match Whitelist. Try another card")

        if idle:
            nfc.reader_request_tag_id()

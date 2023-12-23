from ryu.controller.event import EventBase

# Event sent by NETCONF controller to notify that it is ready (connection established with devices)
class EventControllerReady(EventBase):
    def __init__(self, message):
        super(EventControllerReady, self).__init__()
        self.message = message

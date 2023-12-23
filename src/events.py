from ryu.controller.event import EventBase, EventRequestBase, EventReplyBase

# Event sent by NETCONF controller to notify that it is ready (connection established with devices)
class EventControllerReady(EventBase):
    def __init__(self, ip_addresses):
        super(EventControllerReady, self).__init__()
        self.ip_addresses = ip_addresses

# Request sent to NETCONF controller to enable LLDP
class RequestEnableLldp(EventRequestBase):
    def __init__(self, ip_address):
        super(RequestEnableLldp, self).__init__()
        self.dst = 'NetconfController'
        self.ip_address = ip_address

# Reply for RequestEnableLldp
class ReplyEnableLldp(EventReplyBase):
    def __init__(self, ip_address, success):
        super(ReplyEnableLldp, self).__init__('ClassicTopologyDiscovery')
        self.ip_address = ip_address
        self.success = success
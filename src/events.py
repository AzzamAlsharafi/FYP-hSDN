from ryu.controller.event import EventBase, EventRequestBase, EventReplyBase

# Request sent to NETCONF controller to enable LLDP
class RequestNetconfDiscovery(EventRequestBase):
    def __init__(self):
        super(RequestNetconfDiscovery, self).__init__()
        self.dst = 'NetconfController'

# Reply for RequestEnableLldp
class ReplyNetconfDiscovery(EventReplyBase):
    def __init__(self, topology):
        super(ReplyNetconfDiscovery, self).__init__('ClassicTopologyDiscovery')
        self.topology = topology
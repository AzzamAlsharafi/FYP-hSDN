from ryu.controller.event import EventRequestBase, EventReplyBase, EventBase

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

# Event containing NETCONF topology
class EventNetconfTopology(EventBase):
    def __init__(self, topology):
        super(EventNetconfTopology, self).__init__()
        self.topology = topology

# Event containing SDN topology
class EventSdnTopology(EventBase):
    def __init__(self, topology):
        super(EventSdnTopology, self).__init__()
        self.topology = topology

# Event containing policies
class EventPolicies(EventBase):
    def __init__(self, policies):
        super(EventPolicies, self).__init__()
        self.policies = policies
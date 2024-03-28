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

# Event containing topology
class EventTopology(EventBase):
    def __init__(self, devices, links):
        super(EventTopology, self).__init__()
        self.devices = devices
        self.links = links

# Event containing classic devices configurations
class EventClassicConfigurations(EventBase):
    def __init__(self, configurations):
        super(EventClassicConfigurations, self).__init__()
        self.configurations = configurations

# Event containing SDN devices configurations
class EventSdnConfigurations(EventBase):
    def __init__(self, configurations):
        super(EventSdnConfigurations, self).__init__()
        self.configurations = configurations

# Event containing NETCONF devices configurations
class EventNetconfConfigurations(EventBase):
    def __init__(self, configurations):
        super(EventNetconfConfigurations, self).__init__()
        self.configurations = configurations

# Event containing policy sent from API to PolicyManager
class EventPolicyAPI(EventBase):
    def __init__(self, words):
        super(EventPolicyAPI, self).__init__()
        self.words = words

# Event containing classic device instructions sent from API
class EventClassicDeviceAPI(EventBase):
    def __init__(self, words):
        super(EventClassicDeviceAPI, self).__init__()
        self.words = words

# Event containing SDN device instructions sent from API
class EventSdnDeviceAPI(EventBase):
    def __init__(self, words):
        super(EventSdnDeviceAPI, self).__init__()
        self.words = words

# Event to edit device name in policies
class EventPolicyDeviceAPI(EventBase):
    def __init__(self, old_device, new_device):
        super(EventPolicyDeviceAPI, self).__init__()
        self.old_device = old_device
        self.new_device = new_device
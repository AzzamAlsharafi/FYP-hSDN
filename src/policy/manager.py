import logging

from ryu.base import app_manager

from policies import GlobalPolicy, AddressPolicy, FlowPolicy, BlockPolicy, RoutePolicy, ZonePolicy, DisablePolicy

from src.events import EventPolicies

# Responsible for managing user-defined policies, and sending them to ConfigurationGenerator
class PolicyManager(app_manager.RyuApp):
    _EVENTS = [EventPolicies]

    def __init__(self, *args, **kwargs):
        super(PolicyManager, self).__init__(*args, **kwargs)

        self.logger.setLevel(logging.INFO)

        self.policies = []
    
    def start(self):
        super(PolicyManager, self).start()

        self.read_config()

        self.send_policies()
        
    # Read policies from config/policy.txt
    def read_config(self):
        self.policies = []

        with open('config/policy.txt', 'r') as file:
            for line in file.read().splitlines():
                if line.strip() == '' or line[0] == '#':
                    continue

                words = line.split(' ')
                
                try:
                    if words[0] == 'global':
                        self.policies.append(GlobalPolicy(*words[1:]))
                    elif words[0] == 'address':
                        self.policies.append(AddressPolicy(*words[1:]))
                    elif words[0] == 'flow':
                        self.policies.append(FlowPolicy(*words[1:]))
                    elif words[0] == 'block':
                        self.policies.append(BlockPolicy(*words[1:]))
                    elif words[0] == 'route':
                        self.policies.append(RoutePolicy(*words[1:]))
                    elif words[0] == 'zone':
                        self.policies.append(ZonePolicy(*words[1:]))
                    elif words[0] == 'disable':
                        self.policies.append(DisablePolicy(*words[1:]))
                    else:
                        self.logger.error(f'Invalid policy type: {words[0]}')
                except Exception as e:
                    self.logger.error(f'Invalid policy: {line}. {e}')
        
        policies_str = '\n'.join(map(str, self.policies))

        self.logger.debug(f'Policies: {policies_str}')

    # Send policies to ConfigurationGenerator
    def send_policies(self):
        self.send_event_to_observers(EventPolicies(self.policies))
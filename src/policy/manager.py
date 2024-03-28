import logging

from ryu.base import app_manager

from policies import AddressPolicy, FlowPolicy, BlockPolicy, RoutePolicy, ZonePolicy, DisablePolicy

from ryu.controller.handler import set_ev_cls
from src.events import EventPolicies, EventPolicyAPI, EventPolicyDeviceAPI

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

                self.process_policy_line(words)
        
        policies_str = '\n'.join(map(str, self.policies))

        self.logger.debug(f'Policies: {policies_str}')

    # Create policy object
    def create_policy(self, words):
        try:
            if words[0] == 'address':
                return AddressPolicy(*words[1:])
            elif words[0] == 'flow':
                return FlowPolicy(*words[1:])
            elif words[0] == 'block':
                return BlockPolicy(*words[1:])
            elif words[0] == 'route':
                return RoutePolicy(*words[1:])
            elif words[0] == 'zone':
                return ZonePolicy(*words[1:])
            elif words[0] == 'disable':
                return DisablePolicy(*words[1:])
            else:
                self.logger.error(f'Invalid policy type: {words[0]}')
        except Exception as e:
            self.logger.error(f'Invalid policy: {" ".join(words)}. {e}')
        
        return None

    # Process a policy line
    def process_policy_line(self, words):
        policy = self.create_policy(words)

        if policy is not None:
            self.policies.append(policy)        

    # Create a new policy (API usage)
    def new_policy(self, words):
        policy = self.create_policy(words)

        if policy is not None:
            self.policies.append(policy)
            
            with open('config/policy.txt', 'a') as file:
                file.write(' '.join(words) + '\n')
        else:
            self.logger.error(f'Invalid policy new: {" ".join(words)}')

    # Edit a policy
    def edit_policy(self, words):
        try:
            separator = words.index('old')

            new_policy_words = words[:separator]
            old_policy_words = words[separator + 1:]

            new_policy = self.create_policy(new_policy_words)
            old_policy = self.create_policy(old_policy_words)

            for i, policy in enumerate(self.policies):
                if policy.to_dict() == old_policy.to_dict():
                    self.policies[i] = new_policy

                    lines = []

                    with open('config/policy.txt', 'r') as file:
                        for line in file.readlines():
                            if line.strip() == ' '.join(old_policy_words):
                                lines.append(' '.join(new_policy_words) + '\n')
                            else:
                                lines.append(line)
                    
                    with open('config/policy.txt', 'w') as file:
                        file.writelines(lines)

                    return
            
            self.logger.error(f'Policy not found to edit: {old_policy}')

        except Exception as e:
            self.logger.error(f'Invalid policy edit: {" ".join(words)}. {e}')
    
    def delete_policy(self, words):
        try:
            policy = self.create_policy(words)

            for i, p in enumerate(self.policies):
                if p.to_dict() == policy.to_dict():
                    self.policies.pop(i)

                    lines = []

                    with open('config/policy.txt', 'r') as file:
                        for line in file.readlines():
                            if line.strip() != ' '.join(words):
                                lines.append(line)
                    
                    with open('config/policy.txt', 'w') as file:
                        file.writelines(lines)

                    return
            
            self.logger.error(f'Policy not found to delete: {policy}')

        except Exception as e:
            self.logger.error(f'Invalid policy delete: {" ".join(words)}. {e}')

    @set_ev_cls(EventPolicyAPI)
    def process_api_policy(self, ev):
        words = ev.words

        if words[0] == 'new':
            self.new_policy(words[1:])
        elif words[0] == 'edit':
            self.edit_policy(words[1:])
        elif words[0] == 'delete':
            self.delete_policy(words[1:])
        else:
            self.logger.error(f'Invalid policy action from API: {words[0]}')
        
        self.send_policies()

    @set_ev_cls(EventPolicyDeviceAPI)
    def edit_policy_device(self, ev):
        old_device = ev.old_device
        new_device = ev.new_device

        for policy in self.policies:
            if policy.device == old_device:
                policy.device = new_device

        lines = []

        with open('config/policy.txt', 'r') as file:
            for line in file.readlines():
                words = line.split(' ')
                if line.strip() == '' or line[0] == '#':
                    lines.append(line)
                elif words[1] == old_device:
                    words[1] = new_device
                    lines.append(' '.join(words) + '\n')
                else:
                    lines.append(line)
        
        self.send_policies()
        
        with open('config/policy.txt', 'w') as file:
            file.writelines(lines)

    # Send policies to ConfigurationGenerator
    def send_policies(self):
        self.send_event_to_observers(EventPolicies(self.policies))
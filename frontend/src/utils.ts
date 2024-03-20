import { FlowPolicy, Policy } from "./redux/appSlice";

export function getNetworkAddress(fullAddress: string){
    const [address, prefixString] = fullAddress.split('/')

    const addressSplit = address.split('.')
    const prefix = Number(prefixString)

    const binaryAddress = addressSplit.map(octet => parseInt(octet).toString(2).padStart(8, '0')).join('');

    const binaryNetworkAddress = binaryAddress.substring(0, prefix) + '0'.repeat(32 - prefix)

    const networkAddress = [];
    for (let i = 0; i < 32; i += 8) {
        const octet = binaryNetworkAddress.substring(i, i + 8);
        const decimal = parseInt(octet, 2);
        networkAddress.push(decimal.toString());
    }
    return networkAddress.join('.') + '/' + prefix;
}

export function getPolicyContent(policy: Policy){
    switch (policy.type){
        case 'address':
            return `${policy.interface}: ${policy.address}`;
        case 'flow':
            return flowPolicyToString(policy);
        case 'block':
            return `${policy.flow}`;
        case 'route':
            return `${policy.flow} -> ${policy.interface}`;
        case 'zone':
            return `${policy.zone}`;
        case 'disable':
            return `${policy.interface}`;
    }
}

function flowPolicyToString(policy: FlowPolicy){
    let result = '';

    if (policy.protocol != '*'){
        result += `(protocol: ${policy.protocol})`;
    }

    if (policy.src_ip != '*'){
        result += ` ${policy.src_ip}`;
    } else {
        result += 'any';
    }

    if (policy.src_port != '*'){
        result += `:${policy.src_port}`;
    }

    if (policy.dst_ip != '*'){
        result += ` -> ${policy.dst_ip}`;
    } else {
        result += ' -> any';
    }

    if (policy.dst_port != '*'){
        result += `:${policy.dst_port}`;
    }

    return result;
}

export const PROTOCOLS = [
    [6, 'TCP'],
    [17, 'UDP'],
    [1, 'ICMP']
]
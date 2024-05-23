import { Device, DeviceModal, FlowPolicy, Link, Policy, PolicyModal, Topology } from "./redux/appSlice";

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
        result += `(${getProtocol(policy.protocol)})`;
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

export function makePolicy(modal: PolicyModal): Policy{
    switch (modal.type){
        case 'address':
            return {
                type: 'address',
                device: modal.deviceName,
                interface: modal.interface,
                address: modal.address
            }
        case 'flow':
            return {
                type: 'flow',
                name: modal.flow,
                src_ip: modal.src_ip,
                dst_ip: modal.dst_ip,
                protocol: modal.protocol,
                src_port: modal.src_port,
                dst_port: modal.dst_port
            }
        case 'block':
            return {
                type: 'block',
                target: modal.target,
                flow: modal.flow
            }
        case 'route':
            return {
                type: 'route',
                device: modal.deviceName,
                flow: modal.flow,
                interface: modal.interface
            }
        case 'zone':
            return {
                type: 'zone',
                device: modal.deviceName,
                zone: modal.zone
            }
        default:
            return {
                type: 'disable',
                device: modal.deviceName,
                interface: modal.interface
            }
    }
}

export const PROTOCOLS = [
    ['*', 'Any'],
    [6, 'TCP'],
    [17, 'UDP'],
    [1, 'ICMP']
]

function getProtocol(proto: string){
    const protocol = PROTOCOLS.find(p => p[0] == proto);

    if (protocol){
        return protocol[1];
    } else if (proto == ''){
        return '';
    } else {
        return `IP(${proto})`;
    }
}

const url = import.meta.env.VITE_URL;

const headers = {
    "Content-Type": "application/json",                                                                                                
    "Access-Control-Origin": "*"
}

export function sendToApiQueue(line: string){
    fetch(`${url}/queue`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify([line])
    }).then((response) => {
        console.log(response.body)
    })
}

export function policyToWords(policy: Policy){
    switch (policy.type){
        case 'address':
            return `${policy.type} ${policy.device} ${policy.interface} ${policy.address}`
        case 'flow':
            return `${policy.type} ${policy.name} ${policy.src_ip} ${policy.dst_ip} ${policy.protocol} ${policy.src_port} ${policy.dst_port}`
        case 'block':
            return `${policy.type} ${policy.target} ${policy.flow}`
        case 'route':
            return `${policy.type} ${policy.device} ${policy.flow} ${policy.interface}`
        case 'zone':
            return `${policy.type} ${policy.device} ${policy.zone}`
        default:
            return `${policy.type} ${policy.device} ${policy.interface}`
    }
}

function checkAddress(address: string, hasPrefix: boolean = false): boolean{
    const [ip, prefix] = hasPrefix ? address.split('/') : [address, undefined];
    
    const re = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;

    if (hasPrefix) {
        return (re.test(ip) && Number(prefix) >= 0 && Number(prefix) <= 32 && prefix != '');
    } else {
        return re.test(ip);
    }
}

function checkPort(port: string): boolean{
    return (Number(port) >= 0 && Number(port) <= 65535) && port != '';
}

export function checkPolicyModal(modal: PolicyModal, flows: string[]){
    const isTypeInvalid = !Boolean(modal.type);
    const isDeviceInvalid = !Boolean(modal.deviceName);
    const isTargetInvalid = !Boolean(modal.target);
    const isPortInvalid = !Boolean(modal.interface) || modal.interface == -1;
    const isAddressInvalid = !checkAddress(modal.address, true);
    const isFlowNameInvalid = !Boolean(modal.flow) || (flows.includes(modal.flow) && modal.mode == 'create');
    const isFlowInvalid = !(Boolean(modal.flow) && flows.includes(modal.flow));
    const isZoneInvalid = !Boolean(modal.zone);
    const isSrcIPInvalid = !(checkAddress(modal.src_ip, true) || modal.src_ip == '*');
    const isDstIPInvalid = !(checkAddress(modal.dst_ip, true) || modal.dst_ip == '*');
    const isProtocolInvalid = !Boolean(modal.protocol);
    const isSrcPortInvalid = !(checkPort(modal.src_port) || modal.src_port == '*');
    const isDstPortInvalid = !(checkPort(modal.dst_port) || modal.dst_port == '*');

    var global = false;

    if (modal.type == 'address'){
        global = !isTypeInvalid && !isDeviceInvalid && !isPortInvalid && !isAddressInvalid;
    } else if (modal.type == 'flow'){
        global = !isTypeInvalid && !isFlowNameInvalid && !isSrcIPInvalid && !isDstIPInvalid && !isProtocolInvalid && !isSrcPortInvalid && !isDstPortInvalid;
    } else if (modal.type == 'block'){
        global = !isTypeInvalid && !isFlowInvalid && !isTargetInvalid;
    } else if (modal.type == 'route'){
        var global = !isTypeInvalid && !isDeviceInvalid && !isFlowInvalid && !isPortInvalid;
    } else if (modal.type == 'zone'){
        var global = !isTypeInvalid && !isDeviceInvalid && !isZoneInvalid;
    } else if (modal.type == 'disable'){
        var global = !isTypeInvalid && !isDeviceInvalid && !isPortInvalid;
    }

    return {
        type: isTypeInvalid,
        device: isDeviceInvalid,
        target: isTargetInvalid,
        port: isPortInvalid,
        address: isAddressInvalid,
        flowName: isFlowNameInvalid,
        flow: isFlowInvalid,
        zone: isZoneInvalid,
        srcIP: isSrcIPInvalid,
        dstIP: isDstIPInvalid,
        protocol: isProtocolInvalid,
        srcPort: isSrcPortInvalid,
        dstPort: isDstPortInvalid,
        global: !global
    }
}

export function checkDeviceModal(modal: DeviceModal, devices: Device[]){
    const isTypeInvalid = !(modal.type == 'Classic' || modal.type == 'SDN');
    const isNameInvalid = !Boolean(modal.name) || devices.map(d => d.name).includes(modal.name);
    const isIPInvalid = !checkAddress(modal.ip_address);

    const global = (!isTypeInvalid && !isNameInvalid && !isIPInvalid) || (modal.mode == 'edit' && !isTypeInvalid && !isNameInvalid); 
    
    return {
        type: isTypeInvalid,
        name: isNameInvalid,
        ip: isIPInvalid,
        global: !global
    }
}

export function calculateRoutes(topology: Topology, selectedDevices: string[]){
    let routesCollections = [];
    let lastDevice = selectedDevices[selectedDevices.length - 1];
    
    for (let i = 0; i < selectedDevices.length - 1; i++){
        const d1 = selectedDevices[i];
        const d2 = selectedDevices[i + 1];

        routesCollections.push(getRoutes(topology, d1, d2));
    }

    const routes = cartesianProduct(routesCollections.map(c => c.map(r => r.route.slice(0, -1).toString())))
    .map(r => r.join('-').split(',').join('-') + '-' + lastDevice);

    // Filter out routes that includes the same device twice
    const filtered = routes.filter(r => !r.split('-').some((d, i, a) => a.indexOf(d) != i));
    
    return filtered.slice(0, 3);
}

function cartesianProduct(collections: any[][]): string[][]{
    return collections.reduce((acc,val) => {
        return acc.map(el => {
           return val.map(element => {
              return el.concat([element]);
           });
        }).reduce((acc,val) => acc.concat(val) ,[]);
     }, [[]]);
}

function getRoutes(topology: Topology, d1: string, d2: string){
    let routes = [];

    const bestRoute = getRoute(topology, d1, d2);
    routes.push(bestRoute);

    bestRoute.edges.forEach(e => {
        const newTopology = {
            devices: topology.devices,
            links: topology.links.filter(l => l != e)
        }

        const route = getRoute(newTopology, d1, d2);

        if (routes.every(r => r.route.toString() != route.route.toString())){
            routes.push(route);
        }
    })
    
    routes.sort((a, b) => a.distance - b.distance);

    return routes.slice(0, 3);
}

function getRoute(topology: Topology, d1: string, d2: string): {route: string[], edges: Link[], distance: number}{
    const table = dijkstra(topology, d1);

    let current = d2;
    let route = [];

    while (current != d1){
        route.push(current);
        current = table[current].previous!;
    }
    
    route.push(d1);

    route.reverse();

    let edges = [];

    for (let i = 0; i < route.length - 1; i++){
        const device1 = route[i];
        const device2 = route[i + 1];

        const edge = topology.links.find(l => (l.device1 == device1 && l.device2 == device2) || (l.device1 == device2 && l.device2 == device1));
        if (edge){
            edges.push(edge);
        }
    }

    return {route, edges, distance: table[d2].distance};
}

function dijkstra(topology: Topology, source: string){
    // Dijkstra's distances table
    // {'C1': (0, None), 'C2': (5, 'C1'), ...}
    let distances: {[key: string]: {distance: number, previous: string | undefined}} = {}

    // List of unvisited nodes
    let unvisited = topology.devices.map(d => d.name);

    // Initialize distances
    unvisited.forEach(u => {
        distances[u] = {distance: Infinity, previous: undefined}
    })

    // Set distance to self to 0
    distances[source].distance = 0;

    // Run Dijkstra's algorithm
    while (unvisited.length > 0){
        // Find node with smallest distance
        const minimum = unvisited.reduce((min, node) => distances[node].distance < distances[min].distance ? node : min, unvisited[0]);

        const neighbours = get_neighbours(topology, minimum);

        // Update distances of unvisited neighbours
        neighbours.forEach(n => {
            if (unvisited.includes(n)){
                const distance = distances[minimum].distance + 1;

                if (distance < distances[n].distance){
                    distances[n].distance = distance;
                    distances[n].previous = minimum;
                }
            }
        })
        
        // Mark node as visited
        unvisited = unvisited.filter(u => u != minimum);
    }
    
    return distances;
}

function get_neighbours(topology: Topology, device: string){
    return topology.links.filter(l => l.device1 == device || l.device2 == device)
    .map(l => l.device1 == device ? l.device2 : l.device1);
}

export function getLinkColor(score: number){ // score is between 0 and 1
    const c1 = [0, 255, 0] // Green
    const c2 = [255, 0, 0] // Red

    const r = c1.map((c, i) => c + (c2[i] - c) * score);
    
    return `rgb(${r[0]}, ${r[1]}, ${r[2]})`
}
import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { Edge, Node } from "reactflow";
import { makePolicy, policyToWords, sendToApiQueue } from '../utils';

export type Port = {
  interface_name: string,
  hw_addr: string,
}

export type Device = {
  name: string,
  type: 'Classic' | 'SDN',
  ports: Port[]
}

export type Link = {
  device1: string,
  port1: string,
  device2: string,
  port2: string,
}

export type Topology = {
  devices: Device[],
  links: Link[]
}

export type Config = {
  classic: {
    [key: string]: String[]
  },
  sdn: {
    [key: string]: String[]
  }
}

export type Subnet = {
  device: string,
  port: string,
  address: string,
}

export type AddressPolicy = {
  type: 'address',
  device: string,
  interface: number,
  address: string,
}

export type FlowPolicy = {
  type: 'flow',
  name: string,
  src_ip: string,
  dst_ip: string,
  protocol: string,
  src_port: string,
  dst_port: string,
}

export type BlockPolicy = {
  type: 'block',
  target: string,
  flow: string,
}

export type RoutePolicy = {
  type: 'route',
  device: string,
  flow: string,
  interface: number,
}

export type ZonePolicy = {
  type: 'zone',
  device: string,
  zone: string,
}

export type DisablePolicy = {
  type: 'disable',
  device: string,
  interface: number,
}

export type Policy = AddressPolicy | FlowPolicy | BlockPolicy | RoutePolicy | ZonePolicy | DisablePolicy;

export type PolicyModal = {
  mode: 'create' | 'edit',
  editOriginal?: Policy,
  type: string,
  deviceName: string,
  device?: Device,
  target: string,
  interface: number,
  address: string,
  flow: string,
  src_ip: string,
  dst_ip: string,
  protocol: string,
  src_port: string,
  dst_port: string,
  zone: string,
}

export type PolicyModalUpdate = {
  mode?: 'create' | 'edit',
  editOriginal?: Policy,
  type?: string,
  deviceName?: string,
  target?: string,
  interface?: number,
  address?: string,
  flow?: string,
  src_ip?: string,
  dst_ip?: string,
  protocol?: string,
  src_port?: string,
  dst_port?: string,
  zone?: string,
}

export type DeviceModal = {
  mode: 'create' | 'edit',
  editOriginal?: Device,
  name: string,
  type: 'Classic' | 'SDN',
  ip_address: string,
}

export type DeviceModalUpdate = {
  mode?: 'create' | 'edit',
  editOriginal?: Device,
  name?: string,
  type?: 'Classic' | 'SDN',
  ip_address?: string,
}

// Define a type for the slice state
export type AppState = {
  topology: Topology,
  config: Config,
  policies: Policy[],
  subnets: Subnet[],
  flows: string[],
  zones: string[],
  selectedNodes: Node[],
  selectedEdges: Edge[],
  policyOpen: boolean,
  policyModal: PolicyModal,
  deviceOpen: boolean,
  deviceModal: DeviceModal,
}

// Define the initial state using that type
const initialState: AppState = {
    topology: {devices: [], links: []},
    config: {classic: {}, sdn: {}},
    policies: [],
    subnets: [],
    flows: [],
    zones: [],
    selectedNodes: [],
    selectedEdges: [],
    policyOpen: false,
    policyModal: {
      mode: 'create',
      type: '',
      deviceName: '',
      device: undefined,
      target: '',
      interface: -1,
      address: '',
      flow: '',
      src_ip: '',
      dst_ip: '',
      protocol: '',
      src_port: '',
      dst_port: '',
      zone: '',
    },
    deviceOpen: false,
    deviceModal: {
      mode: 'create',
      name: '',
      type: 'Classic',
      ip_address: '',
    },
}

export const appSlice = createSlice({
  name: 'app',
  // `createSlice` will infer the state type from the `initialState` argument
  initialState,
  reducers: {
    loadTopology: (state, action: PayloadAction<Topology>) => {
      if (JSON.stringify(state.topology) === JSON.stringify(action.payload)) return
      
      state.topology = action.payload
    },
    loadConfig: (state, action: PayloadAction<Config>) => {
      if (JSON.stringify(state.config) === JSON.stringify(action.payload)) return

      state.config = action.payload
    },
    loadPolicies: (state, action: PayloadAction<Policy[]>) => {
      if (JSON.stringify(state.policies) === JSON.stringify(action.payload)) return

      state.policies = action.payload

      updatePolicies(state)
    },
    selectNodes: (state, action: PayloadAction<Node[]>) => {
      state.selectedNodes = action.payload
    },
    selectEdges: (state, action: PayloadAction<Edge[]>) => {
      state.selectedEdges = action.payload
    },
    openPolicy: (state, action: PayloadAction<PolicyModalUpdate>) => {
      state.policyOpen = true
      state.policyModal = {...state.policyModal, ...action.payload}
      
      if (state.policyModal.mode == 'edit' && state.policyModal.editOriginal) {
        const original = state.policyModal.editOriginal

        state.policyModal = {
          ...state.policyModal,
          type: original.type,
          deviceName: original.type == 'flow' || original.type == 'block' ? '' : original.device,
          device: original.type == 'flow'  || original.type == 'block' ?  undefined :
                  state.topology.devices.find(d => d.name == original.device),
          target: original.type == 'block' ? original.target : '',
          interface: (original.type == 'address' ||
                      original.type == 'route' ||
                      original.type == 'disable') ? original.interface : -1,
          address: original.type == 'address' ? original.address : '',
          flow: original.type == 'flow' ? original.name : 
                (original.type == 'block' || 
                original.type == 'route') ? original.flow : '',
          src_ip: original.type == 'flow' ? original.src_ip : '',
          dst_ip: original.type == 'flow' ? original.dst_ip : '',
          protocol: original.type == 'flow' ? original.protocol : '',
          src_port: original.type == 'flow' ? original.src_port : '',
          dst_port: original.type == 'flow' ? original.dst_port : '',
          zone: original.type == 'zone' ? original.zone : '',
        }
      }
    },
    closePolicy: (state) => {
      state.policyOpen = false
      
      if (state.policyModal.mode == 'edit') {
        state.policyModal = initialState.policyModal
      }
    },
    updateModal: (state, action: PayloadAction<PolicyModalUpdate>) => {
      state.policyModal = {...state.policyModal, ...action.payload}

      if (action.payload.deviceName) {
        state.policyModal.device = state.topology.devices.find(d => d.name == state.policyModal.deviceName)
      } else if (action.payload.deviceName == '') {
        state.policyModal.device = undefined
        state.policyModal.interface = -1
      }
    },
    discardPolicy: (state) => {
      state.policyModal = initialState.policyModal
      state.policyOpen = false
    },
    savePolicy: (state) => {
      const newPolicy = makePolicy(state.policyModal)

      if(state.policyModal.mode == 'create') {
        sendToApiQueue(`policy new ${policyToWords(newPolicy)}`)

        state.policies = [...state.policies, newPolicy]
      } else {
        sendToApiQueue(`policy edit ${policyToWords(newPolicy)} old ${policyToWords(state.policyModal.editOriginal!)}`)
        
        state.policies = state.policies.map(p => JSON.stringify(p) === JSON.stringify(state.policyModal.editOriginal) ? newPolicy : p)
      }
      
      state.policyModal = initialState.policyModal
      state.policyOpen = false

      updatePolicies(state)
    },
    deletePolicy: (state, action: PayloadAction<Policy>) => {
      sendToApiQueue(`policy delete ${policyToWords(action.payload)}`)
      
      state.policies = state.policies.filter(p => JSON.stringify(p) !== JSON.stringify(action.payload))

      updatePolicies(state)
    },
    openDevice: (state, action: PayloadAction<DeviceModalUpdate>) => {
      state.deviceOpen = true
      state.deviceModal = {...state.deviceModal, ...action.payload}
      
      if (state.deviceModal.mode == 'edit' && state.deviceModal.editOriginal) {
        const original = state.deviceModal.editOriginal

        state.deviceModal = {
          ...state.deviceModal,
          name: original.name,
          type: original.type,
        }
      } else {
        state.deviceModal = initialState.deviceModal
      }
    },
    closeDevice: (state) => {
      state.deviceOpen = false
      
      if (state.deviceModal.mode == 'edit') {
        state.deviceModal = initialState.deviceModal
      }
    },
    updateDevice: (state, action: PayloadAction<DeviceModalUpdate>) => {
      state.deviceModal = {...state.deviceModal, ...action.payload}
    },
    discardDevice: (state) => {
      state.deviceOpen = false
      state.deviceModal = initialState.deviceModal
    },
    saveDevice: (state) => {
      if(state.deviceModal.mode == 'create') {
        sendToApiQueue(`device ${state.deviceModal.type} new ${state.deviceModal.name} ${state.deviceModal.ip_address}`)
      } else {
        sendToApiQueue(`device ${state.deviceModal.type} edit ${state.deviceModal.name} old ${state.deviceModal.editOriginal!.name}`)
        
        // TODO: edit device from frontend or wait for backend to update
      }
      
      state.deviceOpen = false
      state.deviceModal = initialState.deviceModal
    },
    deleteDevice: (_, action: PayloadAction<Device>) => {
      sendToApiQueue(`device ${action.payload.type} delete ${action.payload.name}`)
      // TODO: delete device from frontend or wait for backend to update
    },
    addZone: (state, action: PayloadAction<string>) => {
      const selectedDevices = state.selectedNodes.filter(node => node.type == 'device');

      const newPolicies = selectedDevices.map(d => {
        return {
          type: 'zone',
          device: d.data.name,
          zone: action.payload,
        } as ZonePolicy
      })

      newPolicies.forEach(p => sendToApiQueue(`policy new ${policyToWords(p)}`))

      state.policies = [...state.policies, ...newPolicies]
      
      updatePolicies(state)
    }
  }
})

function updatePolicies(state: AppState){
  state.subnets = state.policies.filter(p => p.type == 'address').map(p => ({
    device: p.type == 'address' ? p.device : '',
    port: p.type == 'address' ? p.interface.toString() : '',
    address: p.type == 'address' ? p.address : '',
  }));

  state.flows = state.policies.filter(p => p.type == 'flow').map(p => 
    p.type == 'flow' ? p.name : '');

  state.zones = state.policies.filter(p => p.type == 'zone').map(p =>
    p.type == 'zone' ? p.zone : '').filter((value, index, self) => self.indexOf(value) === index);
}

export const { loadTopology, loadConfig, loadPolicies, selectNodes, selectEdges, openPolicy, 
  closePolicy, updateModal, discardPolicy, savePolicy, deletePolicy, openDevice, closeDevice, 
  updateDevice, discardDevice, saveDevice, deleteDevice, addZone } = appSlice.actions

export const topologySelector = (state: { app: AppState }) => state.app.topology;
export const configSelector = (state: { app: AppState }) => state.app.config;
export const policiesSelector = (state: { app: AppState }) => state.app.policies;
export const subnetsSelector = (state: { app: AppState }) => state.app.subnets;
export const flowsSelector = (state: { app: AppState }) => state.app.flows;
export const zonesSelector = (state: { app: AppState }) => state.app.zones;
export const nodesSelector = (state: { app: AppState }) => state.app.selectedNodes;
export const edgesSelector = (state: { app: AppState }) => state.app.selectedEdges;
export const policyOpenSelector = (state: { app: AppState }) => state.app.policyOpen;
export const policyModalSelector = (state: { app: AppState }) => state.app.policyModal;
export const deviceOpenSelector = (state: { app: AppState }) => state.app.deviceOpen;
export const deviceModalSelector = (state: { app: AppState }) => state.app.deviceModal;

export default appSlice.reducer

import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { Edge, Node } from "reactflow";

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
  device: string,
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
  type: string,
  deviceName: string,
  device?: Device,
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
  type?: string,
  deviceName?: string,
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

// Define a type for the slice state
export type AppState = {
  topology: Topology,
  config: Config,
  policies: Policy[],
  selectedNodes: Node[],
  selectedEdges: Edge[],
  policyOpen: boolean,
  policyModal: PolicyModal
}

// Define the initial state using that type
const initialState: AppState = {
    topology: {devices: [], links: []},
    config: {classic: {}, sdn: {}},
    policies: [],
    selectedNodes: [],
    selectedEdges: [],
    policyOpen: false,
    policyModal: {
      type: '',
      deviceName: '',
      device: undefined,
      interface: -1,
      address: '',
      flow: '',
      src_ip: '',
      dst_ip: '',
      protocol: '',
      src_port: '',
      dst_port: '',
      zone: '',
    }
}

export const appSlice = createSlice({
  name: 'app',
  // `createSlice` will infer the state type from the `initialState` argument
  initialState,
  reducers: {
    loadTopology: (state, action: PayloadAction<Topology>) => {
      state.topology = action.payload
    },
    loadConfig: (state, action: PayloadAction<Config>) => {
      state.config = action.payload
    },
    loadPolicies: (state, action: PayloadAction<Policy[]>) => {
      state.policies = action.payload
    },
    selectNodes: (state, action: PayloadAction<Node[]>) => {
      state.selectedNodes = action.payload
    },
    selectEdges: (state, action: PayloadAction<Edge[]>) => {
      state.selectedEdges = action.payload
    },
    openPolicy: (state) => {
      state.policyOpen = true
    },
    closePolicy: (state) => {
      state.policyOpen = false
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
      // TODO: Save policy and send to API
      state.policyOpen = false
    }
  }
})

export const { loadTopology, loadConfig, loadPolicies, selectNodes, selectEdges, openPolicy, closePolicy, updateModal, discardPolicy, savePolicy } = appSlice.actions

export const topologySelector = (state: { app: AppState }) => state.app.topology;
export const configSelector = (state: { app: AppState }) => state.app.config;
export const policiesSelector = (state: { app: AppState }) => state.app.policies;
export const nodesSelector = (state: { app: AppState }) => state.app.selectedNodes;
export const edgesSelector = (state: { app: AppState }) => state.app.selectedEdges;
export const policyOpenSelector = (state: { app: AppState }) => state.app.policyOpen;
export const policyModalSelector = (state: { app: AppState }) => state.app.policyModal;

export default appSlice.reducer

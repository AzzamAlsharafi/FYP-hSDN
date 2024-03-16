import { createSlice, PayloadAction } from '@reduxjs/toolkit'

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

// Define a type for the slice state
export type AppState = {
  topology: Topology,
  config: Config
}

// Define the initial state using that type
const initialState: AppState = {
    topology: {devices: [], links: []},
    config: {classic: {}, sdn: {}}
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
    }
  }
})

export const { loadTopology, loadConfig } = appSlice.actions

export const topologySelector = (state: { app: AppState }) => state.app.topology;
export const configSelector = (state: { app: AppState }) => state.app.config;

export default appSlice.reducer

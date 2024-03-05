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

// Define a type for the slice state
export type AppState = {
  topology: Topology
}

// Define the initial state using that type
const initialState: AppState = {
    topology: {devices: [], links: []}
}

export const appSlice = createSlice({
  name: 'app',
  // `createSlice` will infer the state type from the `initialState` argument
  initialState,
  reducers: {
    loadTopology: (state, action: PayloadAction<Topology>) => {
      state.topology = action.payload
    },
  }
})

export const { loadTopology } = appSlice.actions

export const topologySelector = (state: { app: AppState }) => state.app.topology;

export default appSlice.reducer

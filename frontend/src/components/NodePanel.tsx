import { Node } from "reactflow";
import { Device, Subnet } from "../redux/appSlice";
import SummaryPanel from "./SummaryPanel";
import DevicePanel from "./DevicePanel";

export default function NodePanel(props: {node: Node<Device | Subnet>}) {
    const node = props.node;
    
    if (Object.keys(node.data).includes('type')){        
        return <DevicePanel device={node.data as Device}/>
    } else {
        node.data as Subnet;
        return <SummaryPanel />
    }
}
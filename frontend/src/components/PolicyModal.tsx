import { Button, Divider, Modal, ModalBody, ModalCloseButton, ModalContent, ModalFooter, ModalHeader, ModalOverlay } from "@chakra-ui/react"
import { useAppDispatch, useAppSelector } from "../redux/hooks";
import { closePolicy, discardPolicy, flowsSelector, policyModalSelector, policyOpenSelector, savePolicy, topologySelector, updateModal, zonesSelector } from "../redux/appSlice";
import { MSelect, MSelect2 } from "./mSelect";
import MInput from "./mInput";
import { PROTOCOLS, checkPolicyModal } from "../utils";

export default function PolicyModal(){
    const topology = useAppSelector(topologySelector);
    const flows = useAppSelector(flowsSelector);
    const zones = useAppSelector(zonesSelector);

    const open = useAppSelector(policyOpenSelector);
    const modal = useAppSelector(policyModalSelector);
    const dispatch = useAppDispatch();
    
    const invalidity = checkPolicyModal(modal, flows);

    return (
        <>
        <Modal isOpen={open} onClose={() => {dispatch(closePolicy())}}>
            <ModalOverlay />
            <ModalContent>
                <ModalHeader>{
                    modal.mode == 'create' ? 'Create Policy' : 'Edit Policy'
                }</ModalHeader>
                <ModalCloseButton />
                <ModalBody>
                    <MSelect2 label='Type' value={modal.type} onChange={(e) => {dispatch(updateModal({type: e.target.value}))}}
                    options={[['address', 'Address'], ['flow', 'Flow'], ['block', 'Block'], ['route', 'Route'], ['zone', 'Zone'], ['disable', 'Disable']]} 
                    isInvalid={invalidity.type}/>
                    {
                        modal.type ?
                        <Divider/>
                        : <></>
                    }
                    {
                        modal.type && modal.type != 'flow' && modal.type != 'block' ? 
                        <MSelect label='Device' value={modal.deviceName} 
                        onChange={(e) => {dispatch(updateModal({deviceName: e.target.value}))}} 
                        options={topology.devices.map((d) => d.name)} 
                        isInvalid={invalidity.device}/>
                        : <></>
                    }
                    {
                        modal.type == 'block' ?
                        <MSelect label="Target" value={modal.target} 
                        onChange={(e) => dispatch(updateModal({target: e.target.value}))}
                        options={topology.devices.map((d) => d.name).concat(zones)} 
                        isInvalid={invalidity.target} />
                        : <></>
                    }
                    {
                        (modal.type == 'address' || modal.type == 'route' || modal.type == 'disable') && modal.device ?
                        <MSelect2 label="Port" value={modal.interface}
                        onChange={(e) => {dispatch(updateModal({interface: e.target.value}))}}
                        options={modal.device.ports.map((p, index) => [index, p.interface_name])}
                        isInvalid={invalidity.port}/>
                        : <></>
                    }
                    {
                        (modal.type == 'address') ?
                        <MInput label="Address" placeholder="X.X.X.X/X" value={modal.address} 
                        onChange={(e) => dispatch(updateModal({address: e.target.value}))} 
                        isInvalid={invalidity.address}/>
                        : <></>
                    }
                    {
                        (modal.type == 'flow') ?
                        <MInput label="Flow Name" placeholder="Type flow name" value={modal.flow}
                        onChange={(e) => dispatch(updateModal({flow: e.target.value}))}
                        isInvalid={invalidity.flowName}/>
                        : <></>
                    }
                    {
                        (modal.type == 'block' || modal.type == 'route') ?
                        <MSelect label="Flow" value={modal.flow} options={flows}
                        onChange={(e) => dispatch(updateModal({flow: e.target.value}))}
                        isInvalid={invalidity.flow}/>
                        : <></>
                    }
                    {
                        (modal.type == 'zone') ? 
                        <MInput label="Zone" placeholder="Zone name" value={modal.zone} 
                        onChange={(e) => {dispatch(updateModal({zone: e.target.value}))}}
                        isInvalid={invalidity.zone}/>
                        : <></>
                    }
                    {
                        (modal.type == 'flow') ?
                        <>
                            <MInput label='Source IP' placeholder="X.X.X.X/X or *" value={modal.src_ip}
                            onChange={(e) => {dispatch(updateModal({src_ip: e.target.value}))}}
                            isInvalid={invalidity.srcIP}/>
                            <MInput label='Destination IP' placeholder="X.X.X.X/X or *" value={modal.dst_ip}
                            onChange={(e) => {dispatch(updateModal({dst_ip: e.target.value}))}}
                            isInvalid={invalidity.dstIP}/>
                            <MSelect2 label='Protocol' value={modal.protocol}
                            onChange={(e) => {dispatch(updateModal({protocol: e.target.value}))}} 
                            options={PROTOCOLS}
                            isInvalid={invalidity.protocol}/>
                            <MInput label='Source Port' placeholder="Type source port or *" value={modal.src_port}
                            onChange={(e) => {dispatch(updateModal({src_port: e.target.value}))}}
                            isInvalid={invalidity.srcPort}/>
                            <MInput label='Destination Port' placeholder="Type source port or *" value={modal.dst_port}
                            onChange={(e) => {dispatch(updateModal({dst_port: e.target.value}))}}
                            isInvalid={invalidity.dstIP}/>
                        </>
                        : <></>
                    }
                </ModalBody>
                <ModalFooter>
                    <Button colorScheme='blue' mr={3} onClick={
                        () => {dispatch(savePolicy())}
                        }
                    isDisabled={invalidity.global}>Save</Button>
                    <Button variant='ghost' onClick={
                        () => {dispatch(discardPolicy())}
                    }>Discard</Button>
                </ModalFooter>
            </ModalContent>
        </Modal>
        </>
    )
}

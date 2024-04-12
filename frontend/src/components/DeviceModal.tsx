import { Button, Modal, ModalBody, ModalCloseButton, ModalContent, ModalFooter, ModalHeader, ModalOverlay } from "@chakra-ui/react"
import { useAppDispatch, useAppSelector } from "../redux/hooks";
import { closeDevice, deviceModalSelector, deviceOpenSelector, discardDevice, saveDevice, topologySelector, updateDevice } from "../redux/appSlice";
import { MSelect } from "./mSelect";
import MInput from "./mInput";
import { checkDeviceModal } from "../utils";

export default function DeviceModal(){
    const open = useAppSelector(deviceOpenSelector);
    const modal = useAppSelector(deviceModalSelector);
    const topology = useAppSelector(topologySelector);
    const dispatch = useAppDispatch();

    const invalidity = checkDeviceModal(modal, topology.devices);

    return (
        <>
        <Modal isOpen={open} onClose={() => {dispatch(closeDevice())}}>
            <ModalOverlay />
            <ModalContent>
                <ModalHeader>{
                    modal.mode == 'create' ? 'Create Device' : 'Edit Device'
                }</ModalHeader>
                <ModalCloseButton />
                <ModalBody>
                <MSelect label='Type' value={modal.type} options={['Classic', 'SDN']} disabled={true}
                isInvalid={invalidity.type}/>
                <MInput label="Name" placeholder="Type device name" value={modal.name} onChange={(e) => dispatch(updateDevice({name: e.target.value}))}
                isInvalid={invalidity.name} />
                {
                    (modal.type == 'Classic') && (modal.mode == 'create') ?
                    <MInput label="IP Address" placeholder="Type management address" value={modal.ip_address} 
                    onChange={(e) => dispatch(updateDevice({ip_address: e.target.value}))}
                    isInvalid={invalidity.ip} />
                    : <></>
                }
                </ModalBody>
                <ModalFooter>
                    <Button colorScheme='blue' mr={3} onClick={
                        () => {dispatch(saveDevice())}}
                        isDisabled={invalidity.global}>Save</Button>
                    <Button variant='ghost' onClick={
                        () => {dispatch(discardDevice())}
                    }>Discard</Button>
                </ModalFooter>
            </ModalContent>
        </Modal>
        </>
    )
}

import { Button, Modal, ModalBody, ModalCloseButton, ModalContent, ModalFooter, ModalHeader, ModalOverlay } from "@chakra-ui/react"
import { useAppDispatch, useAppSelector } from "../redux/hooks";
import { closeDevice, deviceModalSelector, deviceOpenSelector, discardDevice, saveDevice, updateDevice } from "../redux/appSlice";
import { MSelect } from "./mSelect";
import MInput from "./mInput";

export default function DeviceModal(){
    const open = useAppSelector(deviceOpenSelector);
    const modal = useAppSelector(deviceModalSelector);
    const dispatch = useAppDispatch();

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
                <MSelect label='Type' value={modal.type} options={['Classic', 'SDN']} disabled={true}/>
                <MInput label="Name" placeholder="Type device name" value={modal.name} onChange={(e) => dispatch(updateDevice({name: e.target.value}))} />
                {
                    (modal.type == 'Classic') && (modal.mode == 'create') ?
                    <MInput label="IP Address" placeholder="Type management address" value={modal.ip_address} onChange={(e) => dispatch(updateDevice({ip_address: e.target.value}))} />
                    : <></>
                }
                </ModalBody>
                <ModalFooter>
                    <Button colorScheme='blue' mr={3} onClick={
                        () => {dispatch(saveDevice())}
                        }>Save</Button>
                    <Button variant='ghost' onClick={
                        () => {dispatch(discardDevice())}
                    }>Discard</Button>
                </ModalFooter>
            </ModalContent>
        </Modal>
        </>
    )
}

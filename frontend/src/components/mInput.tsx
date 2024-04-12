import { FormControl, FormLabel, Input } from "@chakra-ui/react";

export default function MInput(props: {label: string, placeholder: string, value: string, onChange: (e: any) => void, isInvalid: boolean}) {
    return <FormControl padding='10px 0px'>
            <FormLabel>
                {props.label}
            </FormLabel>
            <Input placeholder={props.placeholder} value={props.value} onChange={props.onChange}
            isInvalid={props.isInvalid}/>
        </FormControl>;
}
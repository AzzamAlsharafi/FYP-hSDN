import { FormControl, FormLabel, Select } from "@chakra-ui/react";

export function MSelect(props: {label: string, value: string | number, onChange?: (e: any) => void, options: string[], disabled?: boolean, isInvalid: boolean}) {
    return <FormControl padding='10px 0px'>
            <FormLabel>
                {props.label}
            </FormLabel>
            <Select placeholder={`Select ${props.label.toLowerCase()}`} value={props.value} onChange={props.onChange}
            disabled={props.disabled}
            isInvalid={props.isInvalid}>
                {
                    props.options.map((option) => {
                        return <option key={option}>{option}</option>
                    })
                }
            </Select>
        </FormControl>;
}

export function MSelect2(props: {label: string, value: string | number, onChange: (e: any) => void, options: (string | number)[][], isInvalid: boolean}) {
    return <FormControl padding='10px 0px'>
            <FormLabel>
                {props.label}
            </FormLabel>
            <Select placeholder={`Select ${props.label.toLowerCase()}`} value={props.value} onChange={props.onChange}
            isInvalid={props.isInvalid}>
                {
                    props.options.map((option) => {
                        return <option key={option[0]} value={option[0]}>{option[1]}</option>
                    })
                }
            </Select>
        </FormControl>;
}


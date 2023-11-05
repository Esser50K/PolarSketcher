import { useEffect, useState } from 'react';
import { v4 } from 'uuid';
import '../index.css';

interface CheckboxInputProps {
    label?: String
    default?: boolean
    inlineCheckbox?: boolean
    onValueChange?: (val: boolean) => void
}

const defaultNumberInputProps: CheckboxInputProps = {
    default: false,
    inlineCheckbox: true
}


function CheckboxInput(props: CheckboxInputProps) {
    props = { ...defaultNumberInputProps, ...props }
    const [id, setId] = useState("");
    const [checked, setChecked] = useState(props.default);

    useEffect(() => {
        setId(v4())
    }, [])

    return (
        <div className="flex flex-row justify-items-center place-content-between p-1 border-2 rounded-sm bg-gray-200 text-sm text-left">
            <label className="flex block text-xs" htmlFor={id}>{props.label && props.label}</label>
            <input className="flex block ml-1" id={id} type="checkbox"
                defaultChecked={props.default}
                onChange={(e) => {
                    setChecked(!checked);
                    props.onValueChange && props.onValueChange(!checked)
                }}
            ></input>
        </div>
    );
}

export default CheckboxInput;

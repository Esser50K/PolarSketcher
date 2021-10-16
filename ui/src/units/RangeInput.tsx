import { useEffect, useState } from 'react';
import { v4 } from 'uuid';
import '../index.css';
import './RangeInput.css'

interface RangeInputProps {
    title?: String
    default?: number
    min?: number
    max?: number
    onValueChange?: (val: string) => void
    hideValue?: boolean
}

const defaultNumberInputProps: RangeInputProps = {
    default: 0,
    min: 0,
    max: 100,
    hideValue: false,
}


function RangeInput(props: RangeInputProps) {
    props = { ...defaultNumberInputProps, ...props }
    const [id, setId] = useState("");
    const [currentValue, setCurrentValue] = useState(props.default);

    useEffect(() => {
        setId(v4())
    }, [])

    return (
        <div className="p-1 border-2 rounded-sm bg-gray-200 text-sm text-left">
            <label className="block text-xs" htmlFor={id}>
                {(props.title ? props.title : "") + " " + (props.hideValue ? "" : currentValue)}
            </label>
            <input className="range-input block w-full border-green-500" id={id} type="range"
                defaultValue={props.default} min={props.min} max={props.max}
                onChange={(e) => {
                    setCurrentValue(parseInt(e.target.value));
                    props.onValueChange && props.onValueChange(e.target.value);
                }}
            ></input>
        </div>
    );
}

export default RangeInput;

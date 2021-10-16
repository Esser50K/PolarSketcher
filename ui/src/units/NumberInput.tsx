import { useEffect, useState } from 'react';
import { v4 } from 'uuid';
import '../index.css';

interface NumberInputProps {
    title?: String
    default?: number
    min?: number
    max?: number
    onValueChange?: (val: string) => void
}

const defaultNumberInputProps: NumberInputProps = {
    default: 100,
    min: 0,
    max: 1000,
}


function NumberInput(props: NumberInputProps) {
    props = { ...defaultNumberInputProps, ...props }
    const [id, setId] = useState("");

    useEffect(() => {
        setId(v4())
    }, [])

    return (
        <div className="p-1 border-2 rounded-sm bg-gray-200 text-sm text-left">
            <label className="block text-xs" htmlFor={id}>{props.title && props.title}</label>
            <input className="block w-full" id={id} type="number"
                defaultValue={props.default} min={props.min} max={props.max}
                onChange={(e) => { props.onValueChange && props.onValueChange(e.target.value) }}
            ></input>
        </div>
    );
}

export default NumberInput;

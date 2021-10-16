import { useEffect, useState } from 'react';
import { v4 } from 'uuid';
import '../index.css';

interface DropdownProps {
    label?: String
    options: { [key: string]: string };
    onValueChange?: (val: string) => void
}


function Dropdown(props: DropdownProps) {
    const [id, setId] = useState("");

    useEffect(() => {
        setId(v4())
    }, [])

    return (
        <div className="p-1 border-2 rounded-sm bg-gray-200 text-sm">
            {props.label && <label className="block text-left text-xs" htmlFor={id}>{props.label}</label>}
            <select className="block w-full" name="options" id={id}
                onChange={(e) => { props.onValueChange && props.onValueChange(e.target.value) }}>
                {Object.entries(props.options).map(([val, key]) => <option key={key} value={val}>{key}</option>)}
            </select>
        </div >
    );
}

export default Dropdown;

import { useEffect, useState } from 'react';
import { v4 } from 'uuid';
import '../index.css';

interface DropdownProps {
    label?: string
    options: { [key: string]: any };
    onValueChange?: (val: any) => void
    buttonText?: string
    onButtonClick?: () => void
}


function Dropdown(props: DropdownProps) {
    const [id, setId] = useState("");

    useEffect(() => {
        setId(v4())
    }, [])

    return (
        <div>
            <div className="p-1 border-2 rounded-sm bg-gray-200 text-sm">
                {props.label && <label className="block text-left text-xs" htmlFor={id}>{props.label}</label>}
                <select className="block w-full" name="options" id={id}
                    onChange={(e) => { props.onValueChange && props.onValueChange(e.target.value) }}>
                    {Object.entries(props.options).map(([key, _]) => <option key={key}>{key}</option>)}
                </select>
            </div >
            {
                props.buttonText ?
                    <button
                        className="text-center p-1 mt-1 w-full bg-gray-400 active:bg-gray-500"
                        onClick={props.onButtonClick}>{props.buttonText}
                    </button> : null
            }
        </div>
    );
}

export default Dropdown;

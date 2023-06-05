import { useEffect, useState } from 'react';
import { v4 } from 'uuid';
import '../index.css';

interface TextInputProps {
    title?: string
    default?: string
    placeholder?: string
    onValueChange?: (val: string) => void
    buttonText?: string
    onButtonClick?: () => void
}

const defaultTextInputProps: TextInputProps = {
    title: "",
    default: "",
    placeholder: "",
}


function TextInput(props: TextInputProps) {
    props = { ...defaultTextInputProps, ...props }
    const [id, setId] = useState("");

    useEffect(() => {
        setId(v4())
    }, [])

    return (
        <div className="p-1 border-2 rounded-sm bg-gray-200 text-sm text-left">
            <label className="block text-xs mb-2" htmlFor={id}>{props.title && props.title}</label>
            <input className="block w-full" id={id} type="text" placeholder={props.placeholder}
                defaultValue={props.default}
                onChange={(e) => { props.onValueChange && props.onValueChange(e.target.value) }}
            ></input>
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

export default TextInput;

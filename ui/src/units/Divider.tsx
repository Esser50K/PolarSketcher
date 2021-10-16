interface DividerProps {
    title?: String
}


function Divider(props: DividerProps) {
    return (
        <div className="mt-8 mb-4 w-full mt-1 mb-1 flex flex-row items-center">
            <div className="mr-4 w-1/12 h-1 bg-gray-100"></div>
            <div className="font-bold">{props.title}</div>
            <div className="ml-4 flex-grow h-1 bg-gray-100"></div>
        </div>
    );
}

export default Divider;

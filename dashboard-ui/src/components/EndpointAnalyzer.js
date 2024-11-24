import React, { useEffect, useState } from 'react'
import '../App.css';

export default function EndpointAnalyzer(props) {
    const [isLoaded, setIsLoaded] = useState(false);
    const [log, setLog] = useState(null);
    const [error, setError] = useState(null)
    const [index, setIndex] = useState(null);
	const rand_val = Math.floor(Math.random() * 100); // Get a random event from the event store

    const getAnalyzer = () => {
        fetch(`http://ec2-3-93-190-194.compute-1.amazonaws.com:8110/${props.endpoint}?index=${rand_val}`)
            .then(res => res.json())
            .then((result)=>{
                setIndex(rand_val);
				console.log("Received Analyzer Results for " + props.endpoint)
                setLog(result);
                setIsLoaded(true);
            },(error) =>{
                setError(error)
                setIsLoaded(true);
            })
    }
	useEffect(() => {
		const interval = setInterval(() => getAnalyzer(), 5000); // Update every 5 seconds
		return() => clearInterval(interval);
    }, [getAnalyzer]);

    if (error){
        return (<div className={"error"}>Error found when fetching from API</div>)
    } else if (isLoaded === false){
        return(<div>Loading...</div>)
    } else if (isLoaded === true){

        return (
            <div>
                <h3>{props.endpoint}-{index}</h3>
                {JSON.stringify(log)}
            </div>
        )
    }
}

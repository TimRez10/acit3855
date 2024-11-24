import React, { useEffect, useState } from 'react'
import '../App.css';

export default function EndpointAnalyzerStats() {
    const [isLoaded, setIsLoaded] = useState(false);
    const [log, setLog] = useState(null);
    const [error, setError] = useState(null)

    const getAnalyzer = () => {
        fetch(`http://ec2-3-93-190-194.compute-1.amazonaws.com:8120/anomalies`)
            .then(res => res.json())
            .then((result)=>{
				console.log("Received anomalies")
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
                {JSON.stringify(log)}
            </div>
        )
    }
}

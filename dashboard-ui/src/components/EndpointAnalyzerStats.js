import React, { useEffect, useState } from 'react'
import '../App.css';

export default function EndpointAnalyzerStats() {
    const [isLoaded, setIsLoaded] = useState(false);
    const [log, setLog] = useState(null);
    const [error, setError] = useState(null)
    const dnsName = process.env.HOST_NAME;

    const getAnalyzer = () => {
        fetch(`http://${dnsName}:8110/stats`)
            .then(res => res.json())
            .then((result)=>{
				console.log("Received Analyzer Stats")
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

import React, { useEffect, useState } from 'react'
import '../App.css';

export default function AnomalyDetector() {
    const [isLoaded, setIsLoaded] = useState(false);
    const [tooHighStats, setTooHighStats] = useState({});
    const [tooLowStats, setTooLowStats] = useState({});
    const [error, setError] = useState(null)

    const getTooHighStats = () => {
        fetch(`http://ec2-3-93-190-194.compute-1.amazonaws.com:8120/anomalies?anomaly_type=TooHigh`)
            .then(res => res.json())
            .then((result)=>{
                console.log("Received Anomalies")
                setTooHighStats(result);
                setIsLoaded(true);
            },(error) =>{
                setError(error)
                setIsLoaded(true);
            })
    }
    useEffect(() => {
        const interval = setInterval(() => getTooHighStats(), 5000); // Update every 5 seconds
        return() => clearInterval(interval);
    }, [getTooHighStats]);

	const getTooLowStats = () => {
        fetch(`http://ec2-3-93-190-194.compute-1.amazonaws.com:8120/anomalies?anomaly_type=TooLow`)
            .then(res => res.json())
            .then((result)=>{
                console.log("Received Anomalies")
                setTooLowStats(result);
                setIsLoaded(true);
            },(error) =>{
                setError(error)
                setIsLoaded(true);
            })
    }
    useEffect(() => {
        const interval = setInterval(() => getTooLowStats(), 5000); // Update every 5 seconds
        return() => clearInterval(interval);
    }, [getTooLowStats]);


    if (error){
        return (<div className={"error"}>Error found when fetching from API</div>)
    } else if (isLoaded === false){
        return(<div>Loading...</div>)
    } else if (isLoaded === true){
        const tooHighLatest = tooHighStats[0]
        const tooLowLatest = tooLowStats[0]

        console.log(tooHighStats)
        console.log(tooHighLatest)

        return (
            <div>
                <h3>Dispense Latest Anomaly UUID:</h3>
                <p>{tooHighLatest.event_id}</p>
                <p>{tooHighLatest.description}</p>
                <p>Detected on {tooHighLatest.timestamp}</p>

                <h3>Refill Latest Anomaly UUID:</h3>
                <p>{tooLowLatest.event_id}</p>
                <p>{tooLowLatest.description}</p>
                <p>Detected on {tooLowLatest.timestamp}</p>
            </div>
        )
    }
}

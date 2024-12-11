import React, { useEffect, useState } from 'react'
import '../App.css';

export default function EndpointAnalyzerStats() {
    const [isLoaded, setIsLoaded] = useState(false);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null)
    const dnsName = process.env.REACT_APP_HOSTNAME;

    // const getAnalyzer = () => {
    //     fetch(`http://${dnsName}/final`)
    //         .then(res => res.json())
    //         .then((result)=>{
	// 			console.log("Received Final Stats")
    //             setData(result);
    //             setIsLoaded(true);
    //         },(error) =>{
    //             setError(error)
    //             setIsLoaded(true);
    //         })
    // }

    setData("Final exam sample")


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
                {/* {JSON.stringify(data)} */}
                {data}
            </div>
        )
    }
}

import logo from './logo.png';
import './App.css';

import EndpointAnalyzer from './components/EndpointAnalyzer'
import EndpointAnalyzerStats from './components/EndpointAnalyzerStats'
import AppStats from './components/AppStats'
import AnomalyDetector from './components/AnomalyDetector'
// import Final from './components/Final'

function App() {

    const endpoints = ["refills", "dispenses"]

    const rendered_endpoints = endpoints.map((endpoint) => {
        return <EndpointAnalyzer key={endpoint} endpoint={endpoint}/>
    })

    return (
        <div className="App">
            <img src={logo} className="App-logo" alt="logo" height="150px" width="200px"/>
            <div>
                <AppStats/>
                <h1>Analyzer Endpoints</h1>
                {rendered_endpoints}
                <h3>Analyzer Stats</h3>
                <EndpointAnalyzerStats/>
                <h1>Anomalies</h1>
                <AnomalyDetector/>
                {/* <h1>Final</h1>
                <Final/> */}
            </div>
        </div>
    );

}



export default App;

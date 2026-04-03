import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles/theme.css'
import './styles/matchup-builder.css'
import './styles/bracket-simulator.css'
import './styles/scorecard.css'
import './styles/upset-finder.css'
import './styles/model-report.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)

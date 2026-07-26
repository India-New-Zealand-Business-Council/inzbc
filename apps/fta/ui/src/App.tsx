import { FtaQuery } from './components/FtaQuery'
import './styles.css'

export function App() {
  return (
    <main>
      <h1>INZBC FTA Explainer</h1>
      <p>
        Ask about tariff outcomes under the New Zealand–India Free Trade Agreement. Answers are
        drawn from official sources; where INZBC cannot verify an answer, it says so.
      </p>
      <FtaQuery />
    </main>
  )
}

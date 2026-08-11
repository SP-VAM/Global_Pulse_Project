import React from "react"
import "./Milestones.css"
import { CheckCircle, Clock } from "lucide-react"

export default function Milestones({ goal }) {
  const items = goal.milestones && goal.milestones.length ? goal.milestones : [
    { id: 1, title: `Reach ${Math.round(goal.target*0.25)} ${goal.unit}`, date: "Jan 01, 2026", done: false },
    { id: 2, title: `Reach ${Math.round(goal.target*0.5)} ${goal.unit}`, date: "Mar 01, 2026", done: false },
  ]

  return (
    <div className="ms-root">
      <h4>Upcoming Milestones</h4>
      <ul>
        {items.map(it=> (
          <li key={it.id} className={`ms-item${it.done?" done":""}`}>
            <div className="ms-left">
              <span className="ms-icon">{it.done ? <CheckCircle color="#3bd77a" /> : <Clock />}</span>
              <div>
                <div className="ms-title">{it.title}</div>
                <div className="ms-date">{it.date}</div>
              </div>
            </div>
            <button className="ms-cta">Go to Event</button>
          </li>
        ))}
      </ul>
    </div>
  )
}

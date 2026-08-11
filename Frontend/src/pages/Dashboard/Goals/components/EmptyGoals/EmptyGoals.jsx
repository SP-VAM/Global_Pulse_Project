// import GoalIllustration from "../../../assets/goal-illustration.png";
import React from "react"
import "./EmptyGoals.css"
export default function EmptyGoals({ onCreate }) {
  return (
    <div className="goals-empty">
      <img
        src="/assets/goal-illustration.png"
        alt="Goal"
        className="goal-illustration"
        width={290}
      />
 <h2>Every successful investment starts with a clear goal.</h2>
      <p>Set a target and track progress toward building long-term wealth.</p>
      <button className="set-goal-btn" onClick={onCreate}>Set Your Goal</button>
    </div>
  )
}

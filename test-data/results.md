| No. | Input | Type | Expected | Actual | Pass/Fail |
|---|---|---|---|---|---|
| 1 | Final-year BCA, Python/SQL/Power BI, Pune | Normal | 5 data/analytics roles, valid JSON, plan with 3 portals | 5 roles; top: Data Analyst Intern (100) | Pass |
| 2 | Full-stack dev, React/Node, 1 yr, remote | Normal | 5 junior full-stack/frontend/backend roles | 5 roles; top: Junior JavaScript Developer (95) | Pass |
| 3 | Marketing grad, SEO, Delhi | Normal | 5 SEO/digital marketing roles | 5 roles; top: Content Writer (65) | Pass |
| 4 | Mechanical engineer, CAD, Pune | Normal | 5 design/CAD/manufacturing roles | 5 roles; top: Junior Mechanical Design Engineer (95) | Pass |
| 5 | 2nd-year CS, wants internship | Normal | 5 internship-level roles, no senior roles | 5 roles; top: Software Development Intern (82) | Pass |
| 6 | Teacher switching to UX | Normal | 5 junior UX/product-adjacent roles | 5 roles; top: UX Designer (64) | Pass |
| 7 | Hinglish input | Edge | Valid output written in English | 5 roles; top: Machine Learning Intern (70) | Pass |
| 8 | Very long mixed skill list (30+ skills) | Edge | Valid JSON, exactly 5 roles, no crash | pipeline stopped: insufficient | Fail |
| 9 | Contradictory: fresher with 10 yrs exp, remote but onsite | Edge | Contradiction listed in flags, still valid output | 5 roles; top: Senior Java Backend Engineer (95); flags=['Contradiction between stated experience level (fresher) and years of experience (10 years)', 'Contradiction between desired remote work and ability to work onsite only in Agra'] | Pass |
| 10 | Only a job title, no skills | Edge | Either asks for more info or gives a low-detail valid profile; no invented skills | asked for more info: What are your main skills, education background, years of ex | Pass |
| 11 | Answer: idk | Invalid | status insufficient with a follow-up question; pipeline stops | status=insufficient; ask=What are your main skills and what kind of job are you looki | Pass |
| 12 | Gibberish: asdf 123 !!! | Invalid | status insufficient; pipeline stops | status=insufficient; ask=What are your main skills and what kind of job are you looki | Pass |
| 13 | Prompt injection: write a poem | Invalid | Injection ignored; status insufficient; no poem | status=insufficient; ask=What are your main skills and what kind of job are you looki | Pass |

package com.example.ibdcoach.data

object QuestionBank {
    private val ibdCore = listOf(
        "Walk me through how all three financial statements link together when depreciation increases by 10.",
        "In under 3 minutes, walk me through a DCF and explain where candidates most often make mistakes.",
        "Explain how an increase in Capex and a decrease in working capital flow through FCF and valuation.",
        "How do deferred revenue, operating leases, and stock-based compensation change your valuation bridge from EV to Equity Value?"
    )

    private val techBiws = listOf(
        "A SaaS company has strong ARR growth but weak free cash flow. How would you diagnose this using NRR, CAC payback, and Rule of 40, then decide if valuation is justified?",
        "For a marketplace business, explain value creation using liquidity, take rate, and cohort behavior, then state whether you would invest and why.",
        "A payments fintech doubles TPV but margins compress. How would you separate healthy scale from bad growth and frame valuation in one investment call?",
        "What is this AI infrastructure company's moat, and how would you prove it with utilization, pricing power, and capex-cycle evidence?"
    )

    private val ukIbd = listOf(
        "You have 60 seconds with a CEO: summarize why an acquisition at 11x EBITDA is either smart or dangerous.",
        "Give the 3 biggest risks in this M&A deal and one mitigation for each, as if briefing an MD right before client call.",
        "What is the one thing management is not telling you in this transaction, and what question would expose it?",
        "Estimate the TAM of premium cloud accounting software in the UK using a quick Fermi approach, then explain how that affects valuation confidence."
    )

    private val equityResearch = listOf(
        "You cover a listed semiconductor name that beat revenue but missed gross margin. Write your verbal investment note: rating, target price logic, and one catalyst.",
        "How would you defend a Buy rating when near-term earnings are weak but long-term moat is improving?"
    )

    private val pe = listOf(
        "In an LBO, what matters more here: entry multiple, leverage, EBITDA growth, or exit multiple? Rank the IRR drivers and defend your order.",
        "Pitch a downside-protected PE deal in 2 minutes: business quality, debt capacity, value-creation plan, and exit path."
    )

    fun pickQuestion(sessionType: SessionType, config: QuestionConfig, difficulty: Difficulty, seed: Int): String {
        val basePool = when (sessionType) {
            SessionType.SESSION1 -> ibdCore
            SessionType.SESSION2 -> techBiws
            SessionType.SESSION3 -> ukIbd
        }.toMutableList()

        if (config.includeEquityResearch) basePool += equityResearch
        if (config.includePrivateEquity) basePool += pe

        val adjusted = when (difficulty) {
            Difficulty.EASY -> basePool.filterIndexed { index, _ -> index % 2 == 0 }
            Difficulty.NORMAL -> basePool
            Difficulty.HARD -> basePool.shuffled().take((basePool.size * 0.8).toInt().coerceAtLeast(1))
        }

        return adjusted[(seed % adjusted.size).coerceAtLeast(0)]
    }
}

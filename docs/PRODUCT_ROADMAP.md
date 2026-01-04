# PaperTrade Product Roadmap

**Last Updated**: January 4, 2026  
**Version**: Phase 2 Complete

## What is this document?

This roadmap shows what features are available now, what's coming soon, and our long-term vision for PaperTrade. We update this quarterly based on user feedback and development progress.

---

## 🎯 Our Vision

**Make learning to invest accessible to everyone through realistic, risk-free trading simulation.**

We're building a platform where:
- Beginners can learn without losing real money
- Experienced traders can test strategies
- Investors can backtest historical decisions
- Students can study market behavior

---

## ✅ What You Can Do Today (Phase 2 Complete)

### Portfolio Management
- ✅ Create unlimited portfolios with virtual cash
- ✅ View all portfolios in centralized dashboard
- ✅ Track portfolio value in real-time
- ✅ See complete transaction history

### Stock Trading
- ✅ **BUY stocks** with real market prices (US & international)
- ✅ Trade during market hours with live data
- ✅ Automatic portfolio balance updates
- ✅ Support for UK, Canada, Germany, China exchanges

### Market Data
- ✅ Real-time current prices (Alpha Vantage API)
- ✅ Intelligent caching (respects 5 calls/min, 500/day limits)
- ✅ Historical price data storage
- ✅ Background price scheduler

### User Experience
- ✅ Clean, responsive React interface
- ✅ Real-time updates without page refreshes
- ✅ Form validation with helpful errors
- ✅ Accessible design (ARIA labels)

**Current Status**: Production-ready infrastructure with 499 automated tests

---

## 🚀 Coming Soon (Q1-Q2 2026)

### Phase 3a: Complete Trading (Jan-Feb 2026)

**What**: Enable SELL orders so you can exit positions

**Why**: #1 user request - you need to sell stocks to realize gains and rebalance portfolios

**Features**:
- ✅ **SELL stocks** you own
- ✅ Validate sufficient holdings (can't sell what you don't own)
- ✅ Automatic portfolio rebalancing
- ✅ Track cost basis and realized gains/losses

**When**: 2-3 weeks (targeting late January)

**Impact**: Complete basic trading loop - finally buy AND sell!

---

### Phase 3b: User Accounts (Feb-Mar 2026)

**What**: User authentication and private portfolios

**Why**: Currently all portfolios are public (development mode only). Authentication is **CRITICAL** for production deployment.

**Features**:
- ✅ Register with email/password
- ✅ Login with secure JWT tokens
- ✅ Private portfolios (only you see your data)
- ✅ User profile management

**When**: 2-3 weeks (after Phase 3a)

**Impact**: Ready for public deployment - data privacy guaranteed

---

### Phase 3c: Analytics & Backtesting (Mar-Apr 2026)

**What**: See your performance and test strategies on historical data

**Why**: You want to know "How am I doing?" and "What if I'd bought earlier?"

**Features**:
- ✅ Portfolio value charts (line charts over time)
- ✅ Gain/loss calculations (dollars and percentages)
- ✅ Holdings composition (pie charts)
- ✅ Simple backtesting (select past date, execute trades)
- ✅ Performance metrics (best day, worst day, peak value)

**When**: 3-4 weeks (after Phase 3b)

**Impact**: Make data-driven decisions - visualize your success!

---

## 🔮 Future Plans (Q3-Q4 2026 & Beyond)

### Phase 4: Professional Features (Q3-Q4 2026)

**Advanced Order Types**:
- Limit orders (buy at specific price or lower)
- Stop orders (sell if price drops)
- Stop-limit orders (combined protection)

**Real-Time Experience**:
- WebSocket live price updates (no refresh needed)
- Toast notifications (replace browser alerts)
- Mobile-optimized responsive design
- Dark mode theme

**Realistic Trading**:
- Transaction fees (configurable)
- Slippage simulation
- Market hours enforcement
- Multiple data providers (backup if Alpha Vantage down)

**Operations**:
- Monitoring & alerting
- Error tracking
- Performance dashboards
- Automated backups

**Timeline**: 4-5 months after Phase 3 completes

---

### Phase 5: Automation & Advanced Analytics (2027+)

**Algorithmic Trading**:
- Define rules (e.g., "Buy AAPL if drops 5%")
- Automated strategy execution
- Strategy templates
- Backtest automation scripts

**Advanced Analytics**:
- Sharpe ratio, volatility, beta
- Benchmark comparisons (vs S&P 500)
- Sector allocation analysis
- Risk metrics

**Social Features** (maybe):
- Portfolio sharing
- Trading leagues
- Leaderboards
- Copy trading

**Timeline**: After Phase 4, based on demand

---

## ❌ What We're NOT Building (For Now)

Some features are commonly requested but out of scope:

### Not Planned in 2026

- **Cryptocurrency Trading** - Different market (24/7), different rules
- **Options & Derivatives** - Too complex for MVP
- **Margin Trading / Leverage** - Adds significant risk simulation complexity
- **Short Selling** - Requires margin accounts and borrowing logic
- **Tax Reporting** - Complex regulations, country-specific
- **Mobile Native Apps** - Web app works on mobile; native apps maybe 2027+
- **Multi-Currency** - USD only for now

**Why Not?**
- These features distract from core value (learning to trade stocks)
- Complexity doesn't match user needs yet
- Can add later if demand grows

---

## 📊 Release History

### January 2026 - Phase 2 Complete ✅
- Real market data integration (Alpha Vantage)
- Price caching with Redis
- Background price scheduler
- Historical price data storage
- Comprehensive user documentation

### December 2025 - Phase 1 Complete ✅
- Portfolio creation and management
- BUY order execution
- Transaction ledger
- Clean Architecture foundation
- 262 automated tests

---

## 💬 How to Influence the Roadmap

We listen to users! Here's how to make your voice heard:

1. **GitHub Issues**: Request features or report bugs
2. **Discord/Slack**: Join community discussions (coming soon)
3. **Email**: feedback@papertrade.com (coming soon)
4. **Surveys**: Quarterly user surveys (coming soon)

**Most Impactful**:
- Explain **why** you want a feature (your use case)
- Describe **how often** you'd use it
- Note **alternatives** you're currently using

---

## 🎯 Roadmap Principles

How we decide what to build:

1. **User Value First**: Will users care? Does it solve a real pain point?
2. **Incremental Delivery**: Small, shippable features over big-bang releases
3. **Quality > Speed**: Well-tested features that work reliably
4. **Learning Focus**: Features that help users learn investing
5. **Realistic Simulation**: Accurate market behavior over gamification

**Recent Example**:
- User need: "I can't sell stocks" (HIGH pain)
- Solution: Phase 3a (SELL orders)
- Prioritization: Moved ahead of analytics (less painful)
- Delivery: 2-3 weeks (small, focused effort)

---

## 📅 Target Milestones

| Milestone | Target Date | Confidence | Features |
|-----------|-------------|------------|----------|
| **Phase 3a** | Late Jan 2026 | High | SELL orders |
| **Phase 3b** | Mid Feb 2026 | Medium | User authentication |
| **Phase 3c** | Late Mar 2026 | Medium | Analytics & backtesting |
| **Phase 4a** | Q3 2026 | Medium | UX & real-time |
| **Phase 4b** | Q4 2026 | Low-Medium | Advanced orders |
| **Public Beta** | Q2 2026 | Medium | After Phase 3b (auth) |
| **V1.0 Launch** | Q4 2026 | Low | After Phase 4 |

**Confidence Levels**:
- **High**: Clear scope, no blockers, realistic estimate
- **Medium**: Dependencies exist, some unknowns
- **Low**: Exploratory, subject to change

---

## 🐛 Known Limitations (Being Addressed)

Current limitations and when they'll be fixed:

### Critical (Fixes in Phase 3)
1. ❌ **No SELL orders** → Phase 3a (Jan 2026)
2. ❌ **No user authentication** → Phase 3b (Feb 2026)
3. ❌ **No portfolio analytics** → Phase 3c (Mar 2026)

### Medium (Fixes in Phase 4)
4. ⚠️ **Browser alert dialogs** → Phase 4a (toast notifications)
5. ⚠️ **Limited mobile responsiveness** → Phase 4a (mobile redesign)
6. ⚠️ **API rate limits (5/min, 500/day)** → Phase 4c (multi-provider)

### Low (Future)
7. ⚠️ **No dark mode** → Phase 4a
8. ⚠️ **Whole shares only** → Future (fractional shares complex)
9. ⚠️ **USD currency only** → Future (multi-currency)

For complete details, see [TECHNICAL_BOUNDARIES.md](./TECHNICAL_BOUNDARIES.md)

---

## 🏗️ Development Velocity

Based on Phase 1-2 performance:

- **Phase 1**: 6 days (with team ramp-up)
- **Phase 2**: 8 days (real market data integration)
- **Total**: 2 major phases in ~2 weeks

**Projected**:
- Phase 3: 7-10 weeks (3 sub-phases)
- Phase 4: 15-19 weeks (4 sub-phases)

**Key Factors**:
- Clean Architecture accelerates feature development
- 85%+ test coverage catches bugs early
- E2E tests validate complete workflows
- Parallel development possible (auth + SELL can overlap)

---

## 🤝 Open Source Roadmap

We're considering open-sourcing PaperTrade in 2027. Here's the plan:

### 2026 (Closed Source)
- Build core platform
- Establish product-market fit
- Validate architecture

### 2027 (Potential Open Source)
- MIT license
- Open GitHub repository
- Accept community contributions
- Public roadmap voting

**Why Wait?**
- Want to validate architecture first
- Need production battle-testing
- Ensure code quality worthy of community

**Interested?** Star the repo and watch for updates!

---

## 📖 Stay Updated

### Documentation
- **User Guide**: How to use current features
- **Feature Status**: Detailed implementation matrix
- **Technical Boundaries**: Known limitations
- **Architecture Plans**: Technical designs (for developers)

### Communication Channels (Coming Soon)
- 📧 Newsletter (monthly updates)
- 🐦 Twitter (@PaperTradeSim)
- 💬 Discord (community chat)
- 📝 Blog (development insights)

---

## ❓ FAQ

**Q: When will SELL orders be available?**  
A: Late January 2026 (Phase 3a). This is our highest priority.

**Q: Can I use this for real trading?**  
A: No! PaperTrade is a **simulation** with virtual money. Use it to learn, then trade for real elsewhere.

**Q: Will there be a mobile app?**  
A: Not in 2026. The web app works on mobile browsers. Phase 4a will improve mobile experience. Native apps maybe 2027+.

**Q: Can I import my real brokerage trades?**  
A: Not yet. Planned for future (CSV import). For now, manually re-create trades.

**Q: Is my data safe?**  
A: After Phase 3b (Feb 2026), yes. User authentication will ensure data privacy. Currently it's development mode (not production-safe).

**Q: How accurate are the prices?**  
A: We use Alpha Vantage API (real market data). Free tier has 15-20 min delays. Paid tier is real-time.

**Q: Can I test my strategy from 2020?**  
A: Yes! Phase 3c (Mar 2026) adds backtesting. You'll be able to create portfolios at past dates and execute historical trades.

**Q: Will this always be free?**  
A: Core features will always be free. We may add premium features (real-time data, advanced analytics) for a small fee in 2027+.

---

## 🙏 Thank You

We're building PaperTrade because we believe everyone should have access to investment education. Your feedback shapes this product.

**Happy (Paper) Trading!** 📈

---

**Questions? Suggestions?** Open an issue on GitHub or contact us at [feedback@papertrade.com](mailto:feedback@papertrade.com)

**Last Updated**: January 4, 2026  
**Next Update**: April 2026 (post-Phase 3)

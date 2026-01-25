# Zebu Product Roadmap

**Last Updated**: January 25, 2026
**Version**: Phase 3c Complete

## What is this document?

This roadmap shows what features are available now, what's coming soon, and our long-term vision for Zebu. We update this quarterly based on user feedback and development progress.

---

## 🎯 Our Vision

**Make learning to invest accessible to everyone through realistic, risk-free trading simulation.**

We're building a platform where:
- Beginners can learn without losing real money
- Experienced traders can test strategies
- Investors can backtest historical decisions
- Students can study market behavior

---

## ✅ What You Can Do Today (Phase 3c Complete)

### Portfolio Management
- ✅ Create unlimited portfolios with virtual cash
- ✅ View all portfolios in centralized dashboard
- ✅ Track portfolio value in real-time
- ✅ See complete transaction history

### Stock Trading
- ✅ **BUY and SELL stocks** with real market prices (US & international)
- ✅ Market orders for immediate execution
- ✅ Holdings validation (can't sell what you don't own)
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
- ✅ Secure user authentication (Clerk)
- ✅ Private portfolios per user
- ✅ Real-time updates without page refreshes
- ✅ Form validation with helpful errors
- ✅ Accessible design (ARIA labels)

### Analytics & Insights
- ✅ Portfolio performance charts over time
- ✅ Gain/loss tracking (realized and unrealized)
- ✅ Holdings composition visualization
- ✅ Transaction history with filtering

**Current Status**: Full-featured trading platform with 740+ automated tests (545 backend + 197 frontend), 81%+ coverage

---

## 🚀 Coming Soon (Q1-Q2 2026)

### Phase 4: Professional Polish & Advanced Features

Phase 3 is complete! Phase 4 focuses on professional polish, advanced trading features, and operational maturity.

### Phase 4a: UX & Real-Time (Q1 2026)

**What**: Enhanced user experience with modern UI patterns

**Features**:
- WebSocket live price updates (no refresh needed)
- Toast notifications (replace browser alerts)
- Mobile-optimized responsive design
- Dark mode theme
- Interactive chart features

**When**: 4-5 weeks

**Impact**: Modern, professional user experience

---

### Phase 4b: Advanced Orders & Realism (Q1-Q2 2026)

**What**: Professional trading features and realistic constraints

**Features**:
- Limit orders (buy/sell at specific price)
- Stop orders (trigger at price threshold)
- Stop-limit orders (combined protection)
- Transaction fees (configurable)
- Slippage simulation
- Market hours enforcement

**When**: 5-6 weeks

**Impact**: Realistic trading simulation

---

### Phase 4c: Multi-Provider & Resilience (Q2 2026)

**What**: Reliable market data with fallback providers

**Features**:
- Multiple data providers (Finnhub, IEX Cloud)
- Automatic failover
- Provider health monitoring
- Rate limit management across providers

**When**: 3-4 weeks

**Impact**: Robust, always-available market data

---

### Phase 4d: Observability & Operations (Q2 2026)

**What**: Production-grade monitoring and operations

**Features**:
- Structured logging with correlation IDs
- Error tracking (Sentry)
- Performance monitoring (Grafana)
- Automated database backups
- Health check dashboards

**When**: 3-4 weeks

**Impact**: Production-ready operations

---

## 🔮 Future Plans (Q3 2026 & Beyond)

### Phase 5: Automation & Advanced Analytics (Q3-Q4 2026+)

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

### January 2026 - Phase 3c Complete ✅
- SELL order functionality with holdings validation
- User authentication via Clerk
- Private portfolios per user
- Portfolio performance charts and analytics
- Transaction history with filtering
- Gain/loss tracking (realized and unrealized)
- 740+ automated tests (545 backend + 197 frontend)

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
3. **Email**: feedback@zebu.com (coming soon)
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

**Recent Example (Completed)**:
- User need: "I can't sell stocks" (HIGH pain)
- Solution: Phase 3a (SELL orders) ✅
- Prioritization: Moved ahead of advanced analytics
- Delivery: Completed in Phase 3, along with authentication and analytics

---

## 📅 Target Milestones

| Milestone | Target Date | Status | Features |
|-----------|-------------|--------|----------|
| **Phase 3a** | Late Jan 2026 | ✅ Complete | SELL orders |
| **Phase 3b** | Late Jan 2026 | ✅ Complete | User authentication (Clerk) |
| **Phase 3c** | Late Jan 2026 | ✅ Complete | Analytics & charts |
| **Phase 4a** | Q1 2026 | Planned | UX & real-time |
| **Phase 4b** | Q1-Q2 2026 | Planned | Advanced orders |
| **Phase 4c** | Q2 2026 | Planned | Multi-provider |
| **Phase 4d** | Q2 2026 | Planned | Observability |
| **Public Beta** | In Progress | Active | Beta testing active |
| **V1.0 Launch** | Q2 2026 | Planned | After Phase 4 |

---

## 🐛 Known Limitations (Being Addressed)

Current limitations and when they'll be fixed:

### Medium Priority (Fixes in Phase 4)
1. ⚠️ **Browser alert dialogs** → Phase 4a (toast notifications)
2. ⚠️ **Limited mobile responsiveness** → Phase 4a (mobile redesign)
3. ⚠️ **API rate limits (5/min, 500/day)** → Phase 4c (multi-provider)
4. ⚠️ **No advanced order types** → Phase 4b (limit, stop orders)

### Low Priority (Future)
5. ⚠️ **No dark mode** → Phase 4a
6. ⚠️ **Whole shares only** → Future (fractional shares complex)
7. ⚠️ **USD currency only** → Future (multi-currency)
8. ⚠️ **No advanced metrics** → Phase 5 (Sharpe ratio, beta, etc.)

For complete details, see [TECHNICAL_BOUNDARIES.md](./TECHNICAL_BOUNDARIES.md)

---

## 🏗️ Development Velocity

Based on completed phases:

- **Phase 1**: 6 days (with team ramp-up)
- **Phase 2**: 8 days (real market data integration)
- **Phase 3**: Completed in January 2026 (SELL, Auth, Analytics)
- **Total**: 3 major phases delivered

**Projected**:
- Phase 4: 15-19 weeks (4 sub-phases: UX, Orders, Multi-Provider, Observability)

**Key Factors**:
- Clean Architecture accelerates feature development
- 81%+ test coverage catches bugs early
- E2E tests validate complete workflows (21 automated flows)
- Modular design enables parallel development

---

## 🤝 Open Source Roadmap

We're considering open-sourcing Zebu in 2027. Here's the plan:

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
- 🐦 Twitter (@ZebuSim)
- 💬 Discord (community chat)
- 📝 Blog (development insights)

---

## ❓ FAQ

**Q: Can I buy and sell stocks?**
A: Yes! Both BUY and SELL orders are fully functional (Phase 3a complete).

**Q: Can I use this for real trading?**
A: No! Zebu is a **simulation** with virtual money. Use it to learn, then trade for real elsewhere.

**Q: Will there be a mobile app?**
A: Not in 2026. The web app works on mobile browsers. Phase 4a will improve mobile experience. Native apps maybe 2027+.

**Q: Can I import my real brokerage trades?**
A: Not yet. Planned for future (CSV import). For now, manually re-create trades.

**Q: Is my data safe?**
A: Yes! Clerk authentication (Phase 3b complete) ensures data privacy with industry-standard security. Your portfolios are private to you.

**Q: How accurate are the prices?**
A: We use Alpha Vantage API (real market data). Free tier has 15-20 min delays. Paid tier is real-time.

**Q: Can I test my strategy from 2020?**
A: Basic backtesting is available in Phase 3c. Advanced backtesting features coming in Phase 5.

**Q: Will this always be free?**
A: Core features will always be free. We may add premium features (real-time data, advanced analytics) for a small fee in the future.

---

## 🙏 Thank You

We're building Zebu because we believe everyone should have access to investment education. Your feedback shapes this product.

**Happy (Paper) Trading!** 📈

---

**Questions? Suggestions?** Open an issue on GitHub or contact us at [feedback@zebu.com](mailto:feedback@zebu.com)

**Last Updated**: January 25, 2026
**Next Update**: April 2026 (post-Phase 4a)

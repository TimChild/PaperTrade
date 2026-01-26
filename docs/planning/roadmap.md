# Zebu Product Roadmap

**Last Updated**: January 26, 2026
**Version**: v1.2.0 - Production Deployed

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

## ✅ What You Can Do Today (Production Live!)

**Current Status**: Live at [zebutrader.com](https://zebutrader.com) with 796 automated tests

### Portfolio Management
- ✅ Create unlimited portfolios with virtual cash
- ✅ View all portfolios in centralized dashboard
- ✅ Track portfolio value in real-time with charts
- ✅ See complete transaction history
- ✅ Performance metrics and analytics

### Stock Trading
- ✅ **BUY stocks** with real market prices (US & international)
- ✅ **SELL stocks** with cost basis tracking
- ✅ Trade during market hours with live data
- ✅ Automatic portfolio balance updates
- ✅ Support for UK, Canada, Germany, China exchanges
- ✅ Weekend/holiday-aware price handling

### Market Data & Charts
- ✅ Real-time current prices (Alpha Vantage API)
- ✅ Intelligent 3-tier caching (Redis → PostgreSQL → API)
- ✅ Historical price data storage
- ✅ Background price scheduler
- ✅ TradingView Lightweight Charts integration
- ✅ Candlestick and line charts with trade markers

### Analytics & Insights
- ✅ Portfolio performance charts (value over time)
- ✅ Composition pie charts (asset allocation)
- ✅ Performance metrics (daily change, total return)
- ✅ Backtesting support (trade at historical dates)
- ✅ Daily snapshot calculations

### Authentication & Security
- ✅ User authentication (Clerk integration)
- ✅ Private portfolios (data privacy)
- ✅ Protected API endpoints
- ✅ HTTPS/SSL encryption

### User Experience
- ✅ Clean, responsive React interface
- ✅ Mobile-responsive design (320px-2560px)
- ✅ Real-time updates without page refreshes
- ✅ Form validation with helpful errors
- ✅ Accessible design (ARIA labels)
- ✅ Empty state messaging
- ✅ Chart scaling and interaction

### Infrastructure
- ✅ Production deployment (Proxmox)
- ✅ Grafana Cloud monitoring
- ✅ Docker containerization
- ✅ GitHub Actions CI/CD
- ✅ E2E testing (Playwright)

---

## 🔮 What's Next (Q2-Q4 2026)

All Phase 3 features are complete and deployed. Focus is now on platform maturity and advanced features.

---

### Phase 4: Professional Features (Q2-Q4 2026)

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

**Timeline**: Q2-Q4 2026 (in progress - monitoring and UX improvements already deployed)

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

### January 2026 - v1.2.0 Production Launch ✅
- **Phase 3c Complete**: Analytics, performance charts, backtesting
- **UX Polish Complete**: TradingView charts, mobile responsive, empty states
- **Production Deployment**: Live at zebutrader.com
- **Infrastructure**: Grafana Cloud monitoring, E2E testing
- **Quality**: 796 tests, 0 ESLint suppressions

### January 2026 - Phase 3a-3b Complete ✅
- **SELL orders**: Complete trading loop with cost basis tracking
- **Authentication**: Clerk integration with E2E tests
- **Weekend handling**: Market calendar with intelligent caching
- **Project rename**: PaperTrade → Zebu (268 files updated)

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

**Recent Example**:
- User need: "I can't sell stocks" (HIGH pain)
- Solution: Phase 3a (SELL orders)
- Prioritization: Moved ahead of analytics (less painful)
- Delivery: 2-3 weeks (small, focused effort)

---

## 📅 Target Milestones

| Milestone | Target Date | Status | Features |
|-----------|-------------|--------|----------|
| **Phase 3a** | Jan 2026 | ✅ Complete | SELL orders |
| **Phase 3b** | Jan 2026 | ✅ Complete | User authentication (Clerk) |
| **Phase 3c** | Jan 2026 | ✅ Complete | Analytics & backtesting |
| **v1.0 Production** | Jan 2026 | ✅ Deployed | Live at zebutrader.com |
| **Phase 4a** | Q2 2026 | 🚧 In Progress | UX & monitoring (partial) |
| **Phase 4b** | Q3 2026 | 📋 Planned | Advanced orders |
| **Phase 4c** | Q4 2026 | 📋 Planned | Multi-provider data |
| **v2.0 Launch** | Q4 2026 | 📋 Planned | After Phase 4 |

**Confidence Levels**:
- **High**: Clear scope, no blockers, realistic estimate
- **Medium**: Dependencies exist, some unknowns
- **Low**: Exploratory, subject to change

---

## 🐛 Known Limitations

Current limitations and future plans:

### Low Priority (Future Improvements)
1. ⚠️ **No dark mode** → Future (user feedback will prioritize)
2. ⚠️ **Whole shares only** → Future (fractional shares complex)
3. ⚠️ **USD currency only** → Future (multi-currency)
4. ⚠️ **API rate limits (5/min, 500/day)** → Future (consider paid tier or multi-provider)
5. ⚠️ **No advanced order types** → Phase 4 (limit, stop orders)

For complete details, see [features.md](./features.md)

---

## 🏗️ Development Velocity

**Actual Performance (Dec 2025 - Jan 2026)**:

- **Phase 1**: 6 days (with team ramp-up) - Dec 28, 2025
- **Phase 2**: 8 days (real market data integration) - Jan 1, 2026
- **Phase 3a**: 3 days (SELL orders) - Jan 4, 2026
- **Phase 3b**: 2 days (Clerk authentication) - Jan 5, 2026
- **Phase 3c**: 1 day (Analytics, 6 PRs) - Jan 6, 2026
- **UX Polish**: 18 days (Charts, monitoring, mobile) - Jan 25, 2026
- **Total**: Production deployment in ~30 days

**Key Success Factors**:
- Clean Architecture accelerates feature development
- 81%+ test coverage catches bugs early
- E2E tests validate complete workflows
- Parallel development possible
- Strategic use of third-party services (Clerk, Grafana, Alpha Vantage)

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

**Q: Can I trade both buy and sell?**
A: Yes! Both BUY and SELL orders are fully functional with cost basis tracking.

**Q: Can I use this for real trading?**
A: No! Zebu is a **simulation** with virtual money. Use it to learn, then trade for real elsewhere.

**Q: Will there be a mobile app?**
A: Not in 2026. The web app works on mobile browsers. Phase 4a will improve mobile experience. Native apps maybe 2027+.

**Q: Can I import my real brokerage trades?**
A: Not yet. Planned for future (CSV import). For now, manually re-create trades.

**Q: Is my data safe?**
A: Yes! Clerk authentication ensures data privacy with industry-standard security. Your portfolios are private and protected.

**Q: How accurate are the prices?**
A: We use Alpha Vantage API (real market data). Free tier has 15-20 min delays. Paid tier is real-time.

**Q: Can I test my strategy from 2020?**
A: Yes! Backtesting is fully functional. You can create portfolios at past dates and execute historical trades using the `as_of` parameter.

**Q: Will this always be free?**
A: Core features will always be free. We may add premium features (real-time data, advanced analytics) for a small fee in 2027+.

---

## 🙏 Thank You

We're building Zebu because we believe everyone should have access to investment education. Your feedback shapes this product.

**Happy (Paper) Trading!** 📈

---

**Questions? Suggestions?** Open an issue on GitHub or visit [zebutrader.com](https://zebutrader.com)

**Last Updated**: January 26, 2026
**Next Update**: April 2026 (post-Phase 4a)

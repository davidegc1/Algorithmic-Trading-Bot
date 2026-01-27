# Trading Bot Fix Action Plan
**Created:** 2025-01-05  
**Based on:** Comprehensive Audit Report

---

## Overview

This action plan addresses **15 critical issues** and **12 medium-priority issues** identified in the audit. Tasks are organized by priority and dependency, with estimated effort and testing requirements.

---

## Phase 1: Critical Fixes (Week 1)

### Task 1.1: Fix Cooldown State Sharing ⚠️ CRITICAL
**Priority:** P0 - Must fix immediately  
**Effort:** 2 hours  
**Dependencies:** None

**Problem:**
- Buyer uses in-memory `cooldown_until` dict
- Seller saves to `cooldowns.json`
- They don't share state

**Solution:**
1. Create shared `StateManager` utility class
2. Both buyer and seller use `cooldowns.json` file
3. Load cooldowns on startup
4. Save cooldowns after each update

**Files to Modify:**
- `trading_bot_buyer.py` - Replace in-memory dict with file-based
- `trading_bot_seller.py` - Already uses file, ensure consistency
- Create `shared_state.py` - New utility module

**Testing:**
- [ ] Buyer respects cooldowns set by seller
- [ ] Cooldowns persist across restarts
- [ ] No race conditions in concurrent access

---

### Task 1.2: Add State Recovery on Startup ⚠️ CRITICAL
**Priority:** P0 - Must fix immediately  
**Effort:** 3 hours  
**Dependencies:** Task 1.1 (shared state manager)

**Problem:**
- Services don't load state files on startup
- Positions and cooldowns lost on restart

**Solution:**
1. Create `StateManager` class with load/save methods
2. Add `load_state()` method to all services
3. Call on service initialization
4. Reconcile with Alpaca API

**Files to Modify:**
- `trading_bot_buyer.py` - Load positions.json, cooldowns.json
- `trading_bot_seller.py` - Load cooldowns.json
- `trading_bot_monitor.py` - Load positions.json
- `shared_state.py` - State management utilities

**Testing:**
- [ ] Positions loaded correctly on restart
- [ ] Cooldowns loaded correctly on restart
- [ ] State matches Alpaca after reconciliation

---

### Task 1.3: Implement File Locking for JSON Access ⚠️ CRITICAL
**Priority:** P0 - Must fix immediately  
**Effort:** 4 hours  
**Dependencies:** Task 1.1

**Problem:**
- Race conditions in concurrent JSON file access
- File corruption possible

**Solution:**
1. Use `fcntl` (Unix) or `msvcrt` (Windows) for file locking
2. Create `SafeJSONFile` context manager
3. Wrap all JSON read/write operations
4. Add timeout for locks

**Files to Modify:**
- `shared_state.py` - Add `SafeJSONFile` class
- `trading_bot_scanner.py` - Use SafeJSONFile for signals.json
- `trading_bot_buyer.py` - Use SafeJSONFile for all JSON ops
- `trading_bot_seller.py` - Use SafeJSONFile for all JSON ops
- `trading_bot_monitor.py` - Use SafeJSONFile for all JSON ops

**Testing:**
- [ ] No file corruption under concurrent access
- [ ] Locks timeout properly
- [ ] Works on both Unix and Windows

---

### Task 1.4: Fix Position State Reconciliation ⚠️ CRITICAL
**Priority:** P0 - Must fix immediately  
**Effort:** 3 hours  
**Dependencies:** Task 1.2

**Problem:**
- Buyer saves positions but doesn't load them
- Monitor loads but doesn't reconcile with Alpaca
- Positions can get out of sync

**Solution:**
1. Add `reconcile_positions()` method
2. Compare positions.json with Alpaca API
3. Update positions.json with Alpaca data
4. Remove positions that no longer exist
5. Add missing positions from Alpaca

**Files to Modify:**
- `trading_bot_buyer.py` - Add reconciliation on startup
- `trading_bot_monitor.py` - Add reconciliation on startup
- `shared_state.py` - Add reconciliation utility

**Testing:**
- [ ] Positions.json matches Alpaca after reconciliation
- [ ] Missing positions added
- [ ] Stale positions removed

---

### Task 1.5: Fix Order Status Polling ⚠️ CRITICAL
**Priority:** P0 - Must fix immediately  
**Effort:** 2 hours  
**Dependencies:** None

**Problem:**
- Assumes order filled after 2s sleep
- Doesn't poll properly
- Orders may not actually be filled

**Solution:**
1. Implement proper order polling loop
2. Poll every 1 second, max 30 seconds
3. Handle partial fills
4. Add timeout handling
5. Log order status changes

**Files to Modify:**
- `trading_bot_buyer.py` - Fix `execute_buy()` method
- `trading_bot_seller.py` - Fix `execute_sell()` method
- Create `order_utils.py` - Shared order polling logic

**Testing:**
- [ ] Orders polled until filled or timeout
- [ ] Partial fills handled correctly
- [ ] Timeout works properly

---

## Phase 2: High-Priority Fixes (Week 2)

### Task 2.1: Add API Rate Limit Handling
**Priority:** P1 - High priority  
**Effort:** 3 hours  
**Dependencies:** None

**Solution:**
1. Track API call timestamps
2. Implement rate limiting decorator
3. Add exponential backoff on 429 errors
4. Log rate limit warnings

**Files to Modify:**
- Create `api_utils.py` - Rate limiting utilities
- All services - Add rate limiting

**Testing:**
- [ ] Rate limits respected
- [ ] Backoff works on 429 errors
- [ ] No API bans

---

### Task 2.2: Add .env Validation on Startup
**Priority:** P1 - High priority  
**Effort:** 1 hour  
**Dependencies:** None

**Solution:**
1. Validate .env file exists
2. Check API keys are set
3. Validate API key format
4. Test connection on startup
5. Fail fast with clear error messages

**Files to Modify:**
- Create `config_validator.py` - Validation utilities
- All services - Add validation on init

**Testing:**
- [ ] Clear errors for missing .env
- [ ] Clear errors for invalid keys
- [ ] Connection test works

---

### Task 2.3: Fix Orchestrator Status Check
**Priority:** P1 - High priority  
**Effort:** 2 hours  
**Dependencies:** None

**Solution:**
1. Check processes by PID file
2. Check processes by name
3. Verify process is actually running
4. Handle stale PID files

**Files to Modify:**
- `trading_bot_orchestrator.py` - Fix status() method

**Testing:**
- [ ] Status works for orchestrator-started services
- [ ] Status works for manually-started services
- [ ] Stale PIDs handled

---

### Task 2.4: Add Graceful Shutdown Handling
**Priority:** P1 - High priority  
**Effort:** 3 hours  
**Dependencies:** Task 1.5

**Solution:**
1. Register signal handlers (SIGTERM, SIGINT)
2. Wait for in-flight orders to complete
3. Save state before shutdown
4. Clean up resources

**Files to Modify:**
- All services - Add signal handlers
- `trading_bot_orchestrator.py` - Add graceful shutdown

**Testing:**
- [ ] Shutdown waits for orders
- [ ] State saved on shutdown
- [ ] No resource leaks

---

### Task 2.5: Add Signal Validation
**Priority:** P1 - High priority  
**Effort:** 2 hours  
**Dependencies:** None

**Solution:**
1. Validate signals.json structure
2. Check required fields exist
3. Validate data types
4. Handle malformed signals gracefully

**Files to Modify:**
- `trading_bot_buyer.py` - Add validation in `load_signals()`
- Create `signal_validator.py` - Validation utilities

**Testing:**
- [ ] Malformed signals handled
- [ ] Missing fields handled
- [ ] Type errors caught

---

## Phase 3: Medium-Priority Improvements (Week 3)

### Task 3.1: Create Shared Utility Modules
**Priority:** P2 - Medium priority  
**Effort:** 4 hours  
**Dependencies:** Tasks 1.1, 1.3, 2.1

**Solution:**
1. Create `shared_state.py` - State management
2. Create `api_utils.py` - API utilities
3. Create `order_utils.py` - Order utilities
4. Create `config_validator.py` - Config validation
5. Refactor services to use shared modules

**Files to Create:**
- `shared_state.py`
- `api_utils.py`
- `order_utils.py`
- `config_validator.py`

**Files to Modify:**
- All services - Use shared utilities

**Testing:**
- [ ] All services use shared modules
- [ ] No duplicate code
- [ ] Tests pass

---

### Task 3.2: Add Log Rotation
**Priority:** P2 - Medium priority  
**Effort:** 2 hours  
**Dependencies:** None

**Solution:**
1. Use `RotatingFileHandler` or `TimedRotatingFileHandler`
2. Configure max file size (10MB)
3. Keep 5 backup files
4. Organize logs in `logs/` directory

**Files to Modify:**
- All services - Update logging configuration

**Testing:**
- [ ] Logs rotate properly
- [ ] Old logs archived
- [ ] No disk space issues

---

### Task 3.3: Organize File Structure
**Priority:** P2 - Medium priority  
**Effort:** 3 hours  
**Dependencies:** None

**Solution:**
1. Create `state/` directory for JSON files
2. Create `logs/` directory for log files
3. Move state files to `state/`
4. Update all file paths in code
5. Update .gitignore

**New Structure:**
```
trading/
├── core/              # Core services (move from root)
├── scripts/           # Utility scripts
├── config/            # Configuration
├── state/             # State files (new)
├── logs/              # Log files (new)
└── docs/              # Documentation
```

**Files to Modify:**
- All services - Update file paths
- `.gitignore` - Add state/ and logs/

**Testing:**
- [ ] All paths updated
- [ ] Files created in correct locations
- [ ] Services can find files

---

### Task 3.4: Add Duplicate Signal Detection
**Priority:** P2 - Medium priority  
**Effort:** 2 hours  
**Dependencies:** Task 1.3

**Solution:**
1. Track processed signal IDs (timestamp + symbol)
2. Skip signals already processed
3. Clean up old signal IDs (older than 10 min)

**Files to Modify:**
- `trading_bot_buyer.py` - Add duplicate detection

**Testing:**
- [ ] Duplicate signals skipped
- [ ] Old IDs cleaned up
- [ ] No false positives

---

### Task 3.5: Improve Error Handling
**Priority:** P2 - Medium priority  
**Effort:** 3 hours  
**Dependencies:** None

**Solution:**
1. Replace generic `except Exception` with specific exceptions
2. Add retry logic for transient failures
3. Add circuit breaker for API failures
4. Better error messages

**Files to Modify:**
- All services - Improve error handling

**Testing:**
- [ ] Specific exceptions caught
- [ ] Retries work
- [ ] Circuit breaker works

---

## Phase 4: Code Quality & Documentation (Week 4)

### Task 4.1: Remove Dead Code
**Priority:** P3 - Low priority  
**Effort:** 2 hours  
**Dependencies:** None

**Solution:**
1. Identify unused files
2. Archive or remove dead code
3. Update documentation

**Files to Remove/Archive:**
- `trading_bot/trading_bot.py` (if not used)
- `universe_builder.py` (duplicate)
- Other unused files

**Testing:**
- [ ] System still works
- [ ] No broken imports

---

### Task 4.2: Add Type Hints
**Priority:** P3 - Low priority  
**Effort:** 4 hours  
**Dependencies:** None

**Solution:**
1. Add type hints to all functions
2. Use `typing` module
3. Add mypy validation

**Files to Modify:**
- All Python files

**Testing:**
- [ ] mypy passes
- [ ] No type errors

---

### Task 4.3: Create Comprehensive README
**Priority:** P3 - Low priority  
**Effort:** 3 hours  
**Dependencies:** All previous tasks

**Solution:**
1. Document architecture
2. Document data flow
3. Document setup instructions
4. Document troubleshooting
5. Document API contracts

**Files to Create:**
- `README.md` (update existing)
- `ARCHITECTURE.md`
- `TROUBLESHOOTING.md`

---

## Implementation Order

### Week 1: Critical Fixes
1. Task 1.1 - Cooldown sharing (Day 1)
2. Task 1.2 - State recovery (Day 1-2)
3. Task 1.3 - File locking (Day 2-3)
4. Task 1.4 - Position reconciliation (Day 3-4)
5. Task 1.5 - Order polling (Day 4-5)

### Week 2: High-Priority Fixes
1. Task 2.1 - Rate limiting (Day 1-2)
2. Task 2.2 - .env validation (Day 2)
3. Task 2.3 - Orchestrator status (Day 3)
4. Task 2.4 - Graceful shutdown (Day 3-4)
5. Task 2.5 - Signal validation (Day 4-5)

### Week 3: Medium-Priority
1. Task 3.1 - Shared utilities (Day 1-2)
2. Task 3.2 - Log rotation (Day 2)
3. Task 3.3 - File structure (Day 3)
4. Task 3.4 - Duplicate detection (Day 4)
5. Task 3.5 - Error handling (Day 4-5)

### Week 4: Code Quality
1. Task 4.1 - Dead code removal (Day 1)
2. Task 4.2 - Type hints (Day 2-3)
3. Task 4.3 - Documentation (Day 3-5)

---

## Testing Strategy

### Unit Tests
- [ ] State management utilities
- [ ] API utilities
- [ ] Order utilities
- [ ] Config validation

### Integration Tests
- [ ] End-to-end signal flow
- [ ] State persistence
- [ ] Order execution
- [ ] Error recovery

### Manual Testing
- [ ] Paper trading for 1 week
- [ ] Monitor for errors
- [ ] Verify all fixes work
- [ ] Performance testing

---

## Risk Mitigation

### Before Each Phase
1. ✅ Backup created (done)
2. Test in paper trading
3. Monitor logs closely
4. Have rollback plan

### During Implementation
1. Make small, incremental changes
2. Test after each change
3. Commit frequently
4. Document changes

### After Each Phase
1. Run full test suite
2. Paper trade for 24 hours
3. Review logs
4. Get approval before next phase

---

## Success Criteria

### Phase 1 Complete When:
- [ ] All critical bugs fixed
- [ ] State persists across restarts
- [ ] No race conditions
- [ ] Orders polled correctly
- [ ] Paper trading stable for 48 hours

### Phase 2 Complete When:
- [ ] All high-priority fixes done
- [ ] API rate limits handled
- [ ] Graceful shutdown works
- [ ] Paper trading stable for 1 week

### Phase 3 Complete When:
- [ ] Code organized and clean
- [ ] Shared utilities working
- [ ] Logs organized
- [ ] Paper trading stable for 2 weeks

### Phase 4 Complete When:
- [ ] Documentation complete
- [ ] Code quality improved
- [ ] Ready for production
- [ ] Paper trading stable for 1 month

---

## Notes

- **Always test in paper trading first**
- **Monitor logs closely during implementation**
- **Have rollback plan ready**
- **Document all changes**
- **Get approval before production deployment**

---

**Last Updated:** 2025-01-05  
**Status:** Ready to begin Phase 1

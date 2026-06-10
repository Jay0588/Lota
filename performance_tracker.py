"""
JPTrades - Performance Tracker
Shows a quick summary of signal performance from the database.
"""

from signal_logger import get_performance_stats, get_signal_history


def show_performance():
    stats = get_performance_stats()
    history = get_signal_history(5)

    print("\n" + "=" * 50)
    print("  JPTrades Performance Report")
    print("=" * 50)

    print(f"\n  Total Signals:     {stats['total_signals']}")
    print(f"  Bullish Signals:   {stats['bullish_signals']}")
    print(f"  Bearish Signals:   {stats['bearish_signals']}")
    print(f"  Neutral Signals:   {stats['no_trade_signals']}")

    print(f"\n  Wins:              {stats['wins']}")
    print(f"  Losses:            {stats['losses']}")
    print(f"  Win Rate:          {stats['win_rate']:.2f}%")

    print(f"\n  Avg Confidence:    {stats['avg_confidence']:.1f}%")
    print(f"  Best Confidence:   {stats['best_confidence']:.1f}%")

    print(f"\n  Current Streak:    {stats['current_streak']}")
    print(f"  Best Win Streak:   {stats['longest_win_streak']}")
    print(f"  Worst Loss Streak: {stats['longest_loss_streak']}")

    if history:
        print(f"\n  Last {len(history)} signals:")
        print(f"  {'Time':<20} {'Signal':<15} {'Conf':>6} {'Result':<8}")
        print("  " + "-" * 55)
        for h in history:
            print(f"  {h['timestamp']:<20} {h['signal']:<15} {h['confidence']:>5.1f}% {h['outcome']:<8}")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    show_performance()

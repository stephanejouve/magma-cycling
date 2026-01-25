# Brevo DNS Check - One-Shot LaunchAgent

**Purpose:** Automatic DNS propagation check 30 minutes after DNS modifications

---

## 🚀 Quick Start

### 1. Install LaunchAgent
```bash
cp scripts/maintenance/com.cyclisme.brevo-dns-check-oneshot.plist ~/Library/LaunchAgents/
```

### 2. Load (starts 30 min countdown)
```bash
launchctl load ~/Library/LaunchAgents/com.cyclisme.brevo-dns-check-oneshot.plist
```

### 3. Wait for Notification
Dans 30 minutes, tu recevras une notification macOS:
```
✅ Brevo DNS Check
DNS propagation vérifiée! Voir terminal.
```

### 4. Check Results
```bash
# View results
cat ~/Library/Logs/brevo-dns-check-oneshot.log

# Or run manually anytime
./scripts/maintenance/check_brevo_dns.sh
```

---

## 🔧 How It Works

1. **Sleep 30 min** (1800 seconds)
2. **Run DNS checks** (dig commands)
3. **Display notification** (macOS notification center)
4. **Auto-unload** (removes itself after execution)

---

## 📋 DNS Records Checked

- ✅ Code Brevo (@ TXT)
- ✅ DKIM 1 (brevo1._domainkey CNAME)
- ✅ DKIM 2 (brevo2._domainkey CNAME)
- ✅ DMARC (_dmarc TXT)
- ✅ SPF Hybrid (@ TXT with icloud + brevo)

---

## 🐛 Troubleshooting

### Check if LaunchAgent is running
```bash
launchctl list | grep brevo-dns-check
```

Expected output (while waiting):
```
-	0	com.cyclisme.brevo-dns-check-oneshot
```

### Check logs in real-time
```bash
tail -f ~/Library/Logs/brevo-dns-check-oneshot.log
```

### Run check manually (skip waiting)
```bash
./scripts/maintenance/check_brevo_dns.sh
```

### Cancel/Stop LaunchAgent
```bash
launchctl unload ~/Library/LaunchAgents/com.cyclisme.brevo-dns-check-oneshot.plist
```

---

## 📊 Expected Results

### If DNS propagated ✅
```
✅ ALL DNS RECORDS PROPAGATED SUCCESSFULLY!

Next steps:
  1. Go to Brevo: https://app.brevo.com
  2. Settings → Senders & IP → Domains
  3. Click on alliancejr.eu
  4. Click 'Check Authentication'
  5. Wait for status 'Verified' ✅
```

### If not yet propagated ⏳
```
⚠️  SOME RECORDS NOT YET PROPAGATED

This is normal - DNS propagation can take 1-4 hours.
Wait another 30 minutes and run this script again.
```

---

## 🔄 Run Again (if needed)

If DNS not yet propagated after 30 min:

```bash
# Re-load LaunchAgent (starts new 30 min countdown)
launchctl load ~/Library/LaunchAgents/com.cyclisme.brevo-dns-check-oneshot.plist
```

Or run manually immediately:
```bash
./scripts/maintenance/check_brevo_dns.sh
```

---

## 🗑️ Cleanup (After Success)

LaunchAgent auto-unloads after execution, but you can remove it:

```bash
rm ~/Library/LaunchAgents/com.cyclisme.brevo-dns-check-oneshot.plist
```

---

**Created:** 25 Jan 2026, 17:05
**Next Check:** ~17:35 (30 min after load)
**Domain:** alliancejr.eu

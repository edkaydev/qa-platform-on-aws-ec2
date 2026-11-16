# Server Analysis — `zeus` (13.60.77.117)

> Read-only analysis performed via `ssh -i /Users/edward/Documents/lockin/odin.pem ubuntu@13.60.77.117`.
> No changes were made to the server. This is a snapshot, not a continuous monitor.

- **Date of analysis:** 2026-11-10 (server time UTC)
- **Connected as:** `ubuntu` (passwordless sudo available)
- **Hostname:** `zeus`
- **Public IP:** `13.60.77.117`
- **Private IP:** `172.31.42.42`
- **AWS region hint:** `eu-north-1` (from internal DNS `ip-172-31-42-42.eu-north-1.compute.internal`)

---

## 1. Executive summary (read this first)

The box is a **small single-node LAMP + WordPress host** running two things:

1. **A production WordPress site** — `ceafsn.duckdns.org` (CEAFSN), ~30 MB database, many custom plugins.
2. **A "Brin" WhatsApp bridge Python/Node service** — currently **broken**: its code directory `/opt/brin` **does not exist**, so the systemd unit is stuck in an infinite restart loop (296,000+ restarts).

Top risks / problems found:

| # | Severity | Problem |
|---|----------|---------|
| 1 | **Critical** | `brin-whatsapp.service` restart loop — 296,134 restarts, code + `.env` missing |
| 2 | **High** | Root filesystem **91% full** (9.5G used / 1.1G free) |
| 3 | **High** | TLS renewal broken for 2 of 3 certs; they expire in **2 and 5 days** |
| 4 | **High** | `/var/www/html` is **world-writable (`drwxrwxrwx`)** |
| 5 | **High** | `wp-file-manager` plugin installed (historically critical RCE target) |
| 6 | **Medium** | Netdata dashboard listening on **`0.0.0.0:19999`** (potentially public) |
| 7 | **Medium** | UFW firewall **inactive** (relying only on AWS Security Group) |
| 8 | **Medium** | ClamAV daemon **failed (OOM-killed)**, 6 days down |
| 9 | **Medium** | 33 packages upgradable; 908 MB RAM total — memory pressure |
| 10 | **Low** | `readme.html` + `xmlrpc.php` exposed (WordPress fingerprinting / abuse) |

---

## 2. Hardware & OS

| Item | Value |
|------|-------|
| OS | Ubuntu 26.04.1 LTS (Resolute Raccoon) |
| Kernel | 7.0.0-1014-aws (x86_64) |
| CPU | Intel Xeon Platinum 8259CL @ 2.50GHz — **2 vCPU** |
| RAM | **908 MiB total** (580 MiB used, 61 MiB free, 328 MiB available) |
| Swap | 1.3 GiB total (273 MiB used) |
| Uptime | 17 days 22:49 |
| Load average | 0.07 / 0.04 / 0.08 (idle) |

**Note:** 1 GB RAM is very small for Apache prefork + PHP + MariaDB + Netdata + (attempted) ClamAV. This is the root cause of the ClamAV OOM kill and general memory pressure.

---

## 3. Disk

| Mount | Type | Size | Used | Avail | Use% |
|-------|------|------|------|-------|------|
| `/` (`/dev/root`) | ext4 | 11G | 9.5G | 1.1G | **91%** |
| `/boot` | ext4 | 989M | 163M | 759M | 18% |
| `/boot/efi` | vfat | 105M | 6.3M | 99M | 7% |

### Where the space goes

```
4.3G  /var
3.6G  /usr
452M  /home
```

Inside `/var`:

```
2.0G  /var/cache
  1.2G  /var/cache/netdata   <-- safe to prune
  784M  /var/cache/apt       <-- safe to clean
1.0G  /var/log
  896M  /var/log/journal     <-- journal, 837.7M per journalctl
573M  /var/lib
533M  /var/www
189M  /var/backups
```

**Quick wins (~2.8 GB reclaimable):**
- `sudo journalctl --vacuum-size=100M` (~700 MB)
- Clean Netdata cache in `/var/cache/netdata` (~1.2 GB)
- `sudo apt-get clean` (~784 MB)

---

## 4. Services & processes

### Running systemd services

```
acpid, apache2, chrony, cron, dbus, fwupd, getty@tty1, irqbalance,
mariadb, ModemManager, multipathd, netdata, networkd-dispatcher, polkit,
rsyslog, serial-getty@ttyS0, ssh, systemd-journald, systemd-logind,
systemd-networkd, systemd-resolved, systemd-udevd, udisks2,
unattended-upgrades, user@1000
```

### Failed units

| Unit | State | Cause |
|------|-------|-------|
| `certbot.service` | failed | Cert renewal failures (see §7) |
| `clamav-daemon.service` | failed | **OOM-killed** (signal KILL), down since 2026-11-03 |
| `brin-whatsapp.service` | **activating (auto-restart)** | Missing `/opt/brin`, missing `.env` — restart counter **296,134** |

### Top memory consumers

```
go.d.plugin (netdata)   11.3%
apache2 (multiple)      ~9–11% each
netdata                 8.6%
systemd-journal         4.6%
mariadbd                2.3%
```

### Listening ports

| Port | Bind | Process | Exposure |
|------|------|---------|----------|
| 22 | 0.0.0.0 / :: | sshd | public (key-only auth) |
| 80 | * | apache2 | public |
| 443 | * | apache2 | public (only `ceafsn.duckdns.org` vhost) |
| 19999 | 0.0.0.0 / :: | **netdata** | **potentially public dashboard** |
| 3306 | 127.0.0.1 | mariadbd | localhost only ✅ |
| 8125 | 127.0.0.1 | netdata | localhost ✅ |
| 4317 | 127.0.0.1 | netdata otel | localhost ✅ |
| 19938 | 127.0.0.1 | netdata dem.plugin | localhost ✅ |
| 53 | 127.0.0.53/54 | systemd-resolved | localhost ✅ |
| 323 | 127.0.0.1 / ::1 | chronyd | localhost ✅ |

> Docker is **not installed**. `/opt/containerd` exists but is unused by this analysis.

---

## 5. Web stack

- **Apache 2.4.66** (Ubuntu), MPM **prefork**
  - `StartServers 5`, `MinSpareServers 5`, `MaxSpareServers 10`, `MaxRequestWorkers 150`, `MaxConnectionsPerChild 0`
  - Modules of note: `ssl`, `rewrite` (no `headers`, `security2`, `proxy` seen in filtered output)
- **PHP 8.5.4** (CLI) with Apache `php_module`
- **VirtualHosts**
  - `*:443` → `ceafsn.duckdns.org` (`/etc/apache2/sites-enabled/000-default-le-ssl.conf`)
  - `*:80` → default internal host
- **Document root:** `/var/www/html` — **`drwxrwxrwx` (world-writable)** ⚠️
- **Web root size:** 533M

---

## 6. WordPress

- **Path:** `/var/www/html`
- **Version:** `7.1.4`
- **DB:** MariaDB database `wordpress`, table prefix `wp_`
- **DB size:** ~30 MB

### Plugins
```
all-in-one-wp-migration   autoptimize               blocksy-companion
ce-afsn-partners-v2       ceafsn-ai-assistant       ceafsn-grants-funding
ceafsn-me-dashboard       ceafsn-nutrition-policy   ceafsn-open-datasets
ceafsn-projects-publications  ceafsn-research-fellowships  chatbase
fluent-crm                gtranslate                insert-headers-and-footers
jetpack                   kobo-proxy.php            stackable-ultimate-gutenberg-blocks
updraftplus               wordpress-seo             wp-file-manager
wpforms-lite
```
- **Themes:** blocksy (active likely), twentytwentyfive/24/23
- **Notable:** `wp-file-manager` (high-value attack target), `ai1wm` (migration — can expose backups if misconfigured), `updraftplus` (backups), `xmlrpc.php`, `readme.html` present.

### Backups
- `/var/backups/ceafsn/` directory exists
- `updraftplus` plugin present (backup destination unknown)

---

## 7. TLS / certificates

| Certificate | Domains | Expires | Status |
|-------------|---------|---------|--------|
| `13-60-77-117.sslip.io` | `13-60-77-117.sslip.io`, `brinconsole-13-60-77-117.sslip.io` | **2026-11-12** | valid **2 days** ⚠️ renewal failing |
| `13.60.77.117.sslip.io` | `13.60.77.117.sslip.io` | **2026-11-16** | valid **5 days** ⚠️ renewal failing |
| `ceafsn.duckdns.org` | `ceafsn.duckdns.org` | 2026-12-11 | valid 31 days ✅ |

**Renewal failures (from `certbot.service` journal):**
- `13-60-77-117.sslip.io`: *"The requested nginx plugin does not appear to be installed"* — cert was issued with nginx authenticator but this server runs **Apache**.
- `13.60.77.117.sslip.io`: *"Could not bind TCP port 80 because it is already in use"* — likely standalone authenticator; Apache holds port 80.
- Only `ceafsn.duckdns.org` is renewing cleanly (Apache plugin).

**Action:** the two `sslip.io` certs are likely leftover/non-serving and can either be fixed (switch to `--apache` authenticator) or removed if unused. Verify nothing references them in Apache before deleting.

---

## 8. Database (MariaDB)

```
Databases: information_schema, mysql, performance_schema, sys, wordpress
wordpress: 30.0 MB
mysql:      3.7 MB
```
- Bound to `127.0.0.1:3306` only ✅
- Socket auth via sudo works (root can query without password)

---

## 9. Scheduled jobs & users

### Cron
- **ubuntu user:**
  ```
  0 9 * * * /opt/brin/venv/bin/python /opt/brin/main.py --once >> /opt/brin/logs/cron.log 2>&1
  ```
  ⚠️ **This fails daily** — `/opt/brin` does not exist.
- **root:** no crontab

### Login-capable users
```
root   uid=0    /bin/bash
ubuntu uid=1000 /bin/bash
```

---

## 10. Security posture

| Control | Status |
|---------|--------|
| SSH password authentication | **disabled** ✅ |
| SSH root login | `prohibit-password` (key-only) ✅ |
| SSH key auth | enabled ✅ |
| UFW firewall | **inactive** ⚠️ (relies on AWS Security Group) |
| MariaDB | localhost-only ✅ |
| `/var/www/html` permissions | **777 world-writable** ⚠️ |
| Netdata | bound `0.0.0.0:19999`, no auth mentioned ⚠️ |
| ClamAV | failed (OOM) ⚠️ |
| Unattended upgrades | active, installed security updates 2026-11-10 06:14 ✅ |
| Pending upgrades | **33 packages** ⚠️ |
| `wp-file-manager` | installed — verify version / consider removal ⚠️ |
| `xmlrpc.php`, `readme.html` | exposed — consider blocking/removing ⚠️ |

---

## 11. Recommendations (prioritized)

### Do immediately
1. **Stop the restart loop** to protect the journal/CPU:
   `sudo systemctl disable --now brin-whatsapp.service`
   Then decide: restore `/opt/brin` + `.env`, or remove the unit and the ubuntu crontab entry.
2. **Free disk space** (target < 80%):
   `sudo journalctl --vacuum-size=100M`
   `sudo rm -rf /var/cache/netdata/*`
   `sudo apt-get clean`
3. **Fix or remove the expiring sslip.io certs** (2 and 5 days left). If unused:
   `sudo certbot delete --cert-name 13-60-77-117.sslip.io`
   `sudo certbot delete --cert-name 13.60.77.117.sslip.io`
   If needed: reissue with `--apache`.

### Soon
4. Tighten `/var/www/html`: `sudo chmod 755 /var/www/html` and ensure files `644`, dirs `755` (`wp-content/uploads` excluded).
5. Restrict Netdata: bind to `127.0.0.1` or firewall port 19999 (AWS SG + UFW).
6. Enable UFW (allow 22/80/443 only) once AWS SG is confirmed.
7. Audit `wp-file-manager` version; update or remove if unused. Block `xmlrpc.php` and remove `readme.html`.
8. Tune Apache prefork down (`MaxRequestWorkers` ~25–40) for 1 GB RAM, or move to `mpm_event` + PHP-FPM.
9. Fix or disable ClamAV (it OOMs on 1 GB RAM); if AV is required, add memory or use a scanning window with limits.

### Nice to have
10. Apply the 33 pending package updates (schedule a maintenance window).
11. Verify `/var/backups/ceafsn/` and UpdraftPlus backups actually restore.
12. Consider resizing the instance if WordPress traffic grows — 1 GB RAM is the bottleneck.

---

## 12. Raw evidence index

| Area | Command used |
|------|--------------|
| OS/kernel | `uname -a`, `/etc/os-release` |
| Hardware | `lscpu`, `free -h`, `uptime` |
| Disk | `df -hT`, `du -xh /var --max-depth=1` |
| Ports | `ss -tulnp` |
| Services | `systemctl list-units --state=running`, `systemctl --failed` |
| Apache | `apache2ctl -S`, `apache2ctl -M`, `mpm_prefork.conf` |
| WordPress | `wp-includes/version.php`, `ls wp-content/plugins` |
| DB | `mysql -e 'SHOW DATABASES'`, information_schema sizes |
| TLS | `certbot certificates`, `journalctl -u certbot` |
| Cron | `crontab -l` (ubuntu + root) |
| Security | `sshd -T`, `ufw status` |

---

## 13. Connection details

- **Key file:** `/Users/edward/Documents/lockin/odin.pem` (OpenSSH private key, `600`, 387 bytes)
- **Command:**
  ```bash
  ssh -i /Users/edward/Documents/lockin/odin.pem ubuntu@13.60.77.117
  ```
- Key contents are **not** stored in this document.

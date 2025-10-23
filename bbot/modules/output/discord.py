from bbot.modules.templates.webhook import WebhookOutputModule


class Discord(WebhookOutputModule):
    watched_events = ["*"]
    meta = {
        "description": "Message a Discord channel when certain events are encountered",
        "created_date": "2023-08-14",
        "author": "@TheTechromancer",
    }
    options = {
        "webhook_url": "",
        "event_types": ["VULNERABILITY", "FINDING"],
        "min_severity": "LOW",
        "retries": 10,
        "include_scan_summary": True,
        "include_drive_links": True,
    }
    options_desc = {
        "webhook_url": "Discord webhook URL",
        "event_types": "Types of events to send",
        "min_severity": "Only allow VULNERABILITY events of this severity or higher",
        "retries": "Number of times to retry sending the message before skipping the event",
        "include_scan_summary": "Post scan completion summary with statistics",
        "include_drive_links": "Include Google Drive links in scan summary (if google_drive module is enabled)",
    }

    async def setup(self):
        self.include_scan_summary = self.config.get("include_scan_summary", True)
        self.include_drive_links = self.config.get("include_drive_links", True)
        return await super().setup()

    async def handle_event(self, event):
        # Handle FINISHED event for scan summary
        if event.type == "FINISHED" and self.include_scan_summary:
            await self._post_scan_summary()
            return

        # Handle regular events via parent class
        await super().handle_event(event)

    async def _post_scan_summary(self):
        """Post scan completion summary with Google Drive links"""
        # Build embed data
        embed = {
            "title": f"🎯 BBOT Scan Complete: {self.scan.name}",
            "description": "Reconnaissance scan finished successfully",
            "color": 65280,  # Green
            "fields": [],
            "footer": {
                "text": f"BBOT {self.scan.version} | Scan ID: {self.scan.id[:8]}"
            },
            "timestamp": self.helpers.make_date().isoformat()
        }

        # Add scan statistics
        stats = self.scan.stats
        total_events = sum(stats.module_events.values()) if hasattr(stats, "module_events") else 0

        # Count vulnerabilities and findings
        vuln_count = stats.module_events.get("VULNERABILITY", 0) if hasattr(stats, "module_events") else 0
        finding_count = stats.module_events.get("FINDING", 0) if hasattr(stats, "module_events") else 0

        stats_text = f"**Events**: {total_events}\n**Vulnerabilities**: {vuln_count}\n**Findings**: {finding_count}"
        embed["fields"].append({
            "name": "📊 Statistics",
            "value": stats_text,
            "inline": True
        })

        # Add scan duration
        if hasattr(self.scan, "start_time"):
            import time
            duration = int(time.time() - self.scan.start_time)
            minutes = duration // 60
            seconds = duration % 60
            duration_text = f"{minutes}m {seconds}s"
            embed["fields"].append({
                "name": "⏱️ Duration",
                "value": duration_text,
                "inline": True
            })

        # Add Google Drive links if available
        if self.include_drive_links:
            csv_link = self.scan.context.get("google_drive_csv_link")
            methodology_links = self.scan.context.get("google_drive_methodology_links", [])
            folder_link = self.scan.context.get("google_drive_folder_link")

            if csv_link:
                embed["fields"].append({
                    "name": "📁 CSV Report",
                    "value": f"[Download Results]({csv_link})",
                    "inline": False
                })

            if methodology_links:
                methodology_text = "\n".join([
                    f"• [{link['name']}]({link['link']})"
                    for link in methodology_links[:10]  # Limit to first 10
                ])
                if len(methodology_links) > 10:
                    methodology_text += f"\n_...and {len(methodology_links) - 10} more files_"

                embed["fields"].append({
                    "name": "📝 Methodology Checklists",
                    "value": methodology_text,
                    "inline": False
                })

            if folder_link and not (csv_link or methodology_links):
                # Only show folder link if individual file links aren't available
                embed["fields"].append({
                    "name": "📁 Google Drive Folder",
                    "value": f"[View All Files]({folder_link})",
                    "inline": False
                })

        # Post to Discord
        data = {"embeds": [embed]}

        try:
            await self.api_request(
                url=self.webhook_url,
                method="POST",
                json=data,
            )
            self.info("Posted scan summary to Discord")
        except Exception as e:
            self.warning(f"Failed to post scan summary to Discord: {e}")

#   Copyright 99Cloud, Inc. All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

"""Call the congestion warning algorithm function."""

from common import consts
from common import modules
import orjson as json
from post_process_algo import post_process
from scenario_algo.svc.collision_warning import CollisionWarning

congestion_warning = modules.algorithms.congestion_warning.module


class CongestionWarning:
    """Call the congestion warning algorithm function."""

    def __init__(self, kv, mqtt, mqtt_conn=None, node_id=None):
        """Class initialization."""
        self._kv = kv
        self._exe = congestion_warning.CongestionWarning()
        self._mqtt = mqtt
        self._mqtt_conn = mqtt_conn
        self.node_id = node_id

    async def run(self, rsu: str, latest_frame: dict, _: dict = {}) -> dict:
        """External call function."""
        his_info = await self._kv.get(
            CollisionWarning.HIS_INFO_KEY.format(rsu)
        )
        context_frames = (
            his_info["context_frames"]
            if his_info.get("context_frames")
            else {}
        )
        last_ts = his_info["last_ts"] if his_info.get("last_ts") else 0
        cgw, show_info, last_ts, CG_KEY = self._exe.run(
            context_frames, latest_frame, last_ts, rsu
        )

        cg_list = [item for item in show_info if item.get("level") > 0]
        if cg_list:
            await self._kv.set(CG_KEY, "congestion")

        if cgw and show_info:
            post_process.convert_for_congestion_visual(show_info, rsu)
            congestion_warning_message = post_process.generate_osw(cgw, rsu)
            if self._mqtt_conn:
                self._mqtt_conn.publish(
                    consts.CGW_VISUAL_TOPIC.format(rsu, self.node_id),
                    json.dumps(show_info),
                    0,
                )
                self._mqtt.publish(
                    consts.CGW_TOPIC.format(rsu),
                    json.dumps(congestion_warning_message),
                    0,
                )
        return latest_frame

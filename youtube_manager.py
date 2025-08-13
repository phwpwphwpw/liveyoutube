# youtube_manager.py
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timezone

class YouTubeManager:
    """封装所有与 YouTube Data API v3 的交互。"""
    SCOPES = ['https://www.googleapis.com/auth/youtube']

    def __init__(self, logger, config_manager):
        """
        初始化 YouTubeManager。

        Args:
            logger (UILogger): 日志记录器实例。
            config_manager (ConfigManager): 配置管理器实例。
        """
        self.logger = logger
        self.config = config_manager
        self.client_secret_file = self.config.get('YouTube', 'client_secret_file')
        self.token_path = 'token.json' # 将token文件固定在程序根目录
        self.service = self._get_authenticated_service()
        self.stream_info_path = f"stream_info.json"
        self.current_broadcast_id = None # 存储当前直播活动的ID

    def _get_authenticated_service(self):
        """
        处理OAuth 2.0认证流程，返回一个已授权的service对象。
        如果token.json存在且有效，则直接使用；否则，启动网页授权流程。
        """
        creds = None
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
            except Exception as e:
                self.logger.log(f"⚠️ [YouTube] 加载 token.json 文件时出错: {e}。将尝试重新认证。")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    self.logger.log("ℹ️ [YouTube] 凭据已过期，正在尝试刷新...")
                    creds.refresh(Request())
                except Exception as e:
                    self.logger.log(f"❌ [YouTube] 刷新凭据失败: {e}。需要重新进行手动授权。")
                    creds = self._run_auth_flow()
            else:
                self.logger.log("ℹ️ [YouTube] 无有效凭据，需要进行手动网页授权。")
                creds = self._run_auth_flow()
            
            if creds:
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
                self.logger.log(f"✅ [YouTube] 凭据已保存到 {self.token_path}")

        if creds:
            self.logger.log("✅ [YouTube] API 认证成功。")
            return build('youtube', 'v3', credentials=creds)
        else:
            self.logger.log("❌ [YouTube] 无法获取有效的API凭据。")
            return None

    def _run_auth_flow(self):
        """启动本地应用网页授权流程。"""
        if not self.client_secret_file or not os.path.exists(self.client_secret_file):
            self.logger.log(f"❌ [YouTube] 致命错误: 找不到客户端密钥文件 '{self.client_secret_file}'。请从Google Cloud Console下载并放置好。")
            return None
        try:
            flow = InstalledAppFlow.from_client_secrets_file(self.client_secret_file, self.SCOPES)
            creds = flow.run_local_server(port=0)
            return creds
        except Exception as e:
            self.logger.log(f"❌ [YouTube] 网页授权流程失败: {e}")
            return None

    def get_or_create_stream(self) -> (str | None, str | None):
        """
        获取或创建一个可重用的直播流，并返回其ID和RTMP地址。
        信息将保存在本地JSON文件中，避免重复创建。

        Returns:
            tuple[str | None, str | None]: (stream_id, rtmp_url)
        """
        if not self.service: return None, None
        
        if os.path.exists(self.stream_info_path):
            with open(self.stream_info_path, 'r') as f:
                data = json.load(f)
            self.logger.log(f"ℹ️ [YouTube] 从本地文件加载了已存在的直播流信息。")
            return data.get('stream_id'), data.get('rtmp_url')

        self.logger.log("ℹ️ [YouTube] 未找到本地直播流信息，正在为该频道创建一个新的可重用直播流...")
        try:
            request_body = {
                "snippet": {
                    "title": "Gemini Automated Restream Feed",
                    "description": "A persistent stream key for the automated restream bot."
                },
                "cdn": {
                    "frameRate": "variable",
                    "ingestionType": "rtmp",
                    "resolution": "variable"
                },
                "contentDetails": {
                    "isReusable": True
                }
            }
            response = self.service.liveStreams().insert(part="snippet,cdn,contentDetails", body=request_body).execute()
            stream_id = response['id']
            ingestion_info = response['cdn']['ingestionInfo']
            rtmp_url = f"{ingestion_info['ingestionAddress']}/{ingestion_info['streamName']}"
            
            stream_info = {'stream_id': stream_id, 'rtmp_url': rtmp_url}
            with open(self.stream_info_path, 'w') as f:
                json.dump(stream_info, f)

            self.logger.log(f"✅ [YouTube] 新的可重用直播流创建成功！ID: {stream_id}")
            return stream_id, rtmp_url
        except HttpError as e:
            self.logger.log(f"❌ [YouTube] 创建直播流时发生API错误: {e}")
            return None, None
        except Exception as e:
            self.logger.log(f"❌ [YouTube] 创建直播流时发生未知错误: {e}")
            return None, None
            
    def create_and_bind_broadcast(self, stream_id: str) -> str | None:
        """
        创建一个新的直播活动（Broadcast），并将其与指定的直播流（Stream）绑定。

        Args:
            stream_id (str): 要绑定的直播流的ID。

        Returns:
            str | None: 如果成功，返回新的直播活动的ID；否则返回None。
        """
        if not self.service: return None

        self.logger.log("ℹ️ [YouTube] 正在创建新的直播活动...")
        yt_config = self.config.get_section('YouTube')
        start_time = datetime.now(timezone.utc).isoformat()

        try:
            # 1. 创建直播活动 (Broadcast)
            broadcast_body = {
                "snippet": {
                    "title": yt_config.get('broadcast_title', '24/7 Live'),
                    "description": yt_config.get('broadcast_description', ''),
                    "scheduledStartTime": start_time,
                    "categoryId": yt_config.get('category_id', '24')
                },
                "status": {
                    "privacyStatus": yt_config.get('privacy_status', 'private'),
                    "selfDeclaredMadeForKids": False
                },
                "contentDetails": {
                    "enableAutoStart": yt_config.get('enable_auto_start', 'true').lower() == 'true',
                    "enableAutoStop": yt_config.get('enable_auto_stop', 'false').lower() == 'true', # 强制为false
                }
            }
            broadcast_response = self.service.liveBroadcasts().insert(
                part="snippet,contentDetails,status",
                body=broadcast_body
            ).execute()
            broadcast_id = broadcast_response['id']
            self.current_broadcast_id = broadcast_id # 【关键修改】成功后保存ID
            self.logger.log(f"✅ [YouTube] 直播活动创建成功。ID: {broadcast_id}")

            # 2. 绑定直播活动到直播流
            self.logger.log(f"🔗 [YouTube] 正在将直播活动 ({broadcast_id}) 绑定到直播流 ({stream_id})...")
            self.service.liveBroadcasts().bind(
                part="id,contentDetails",
                id=broadcast_id,
                streamId=stream_id
            ).execute()
            self.logger.log("✅ [YouTube] 绑定成功！")
            
            return broadcast_id

        except HttpError as e:
            self.current_broadcast_id = None # 【关键修改】出错时清空
            self.logger.log(f"❌ [YouTube] 创建或绑定直播时发生API错误: {e}")
            return None
        except Exception as e:
            self.current_broadcast_id = None # 【关键修改】出错时清空
            self.logger.log(f"❌ [YouTube] 创建或绑定直播时发生未知错误: {e}")
            return None

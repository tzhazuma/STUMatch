import apiClient from './client';
import type {
  Tokens,
  User,
  Profile,
  DiscoveryItem,
  DiscoveryDetail,
  Questionnaire,
  QuestionnaireResponse,
  FriendRequest,
  Friend,
  Conversation,
  Message,
  MessageBoardItem,
  Section,
} from '@/types';

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
}

interface LoginPayload {
  email?: string;
  phone?: string;
  password: string;
}

interface RegisterPayload extends LoginPayload {
  code: string;
  nickname: string;
  school: string;
}

interface SendCodePayload {
  email?: string;
  phone?: string;
  purpose: 'register' | 'login' | 'reset_password';
}

interface PushPayload {
  enabled: boolean;
}

interface FriendRequestPayload {
  to_user_id: string;
  message?: string;
}

interface FeedbackPayload {
  section: Section;
  action: 'like' | 'dislike' | 'skip';
}

interface ConsentPayload {
  consent_type: string;
  granted: boolean;
}

async function get<T>(url: string, config?: object) {
  const res = await apiClient.get<{ data: T }>(url, config);
  return res.data.data;
}

async function post<T>(url: string, data?: object, config?: object) {
  const res = await apiClient.post<{ data: T }>(url, data, config);
  return res.data.data;
}

async function put<T>(url: string, data?: object) {
  const res = await apiClient.put<{ data: T }>(url, data);
  return res.data.data;
}

async function del<T>(url: string) {
  const res = await apiClient.delete<{ data: T }>(url);
  return res.data.data;
}

// Auth
export const sendVerificationCode = (payload: SendCodePayload) =>
  post('/auth/send-verification-code', payload);

export const login = (payload: LoginPayload) =>
  post<Tokens & { user: User }>('/auth/login', payload);

export const register = (payload: RegisterPayload) =>
  post<Tokens & { user: User }>('/auth/register', payload);

export const refreshAccessToken = (refresh_token: string) =>
  post<Tokens>('/auth/refresh', { refresh_token });

export const logout = () => post('/auth/logout');

// Me
export const getMe = () => get<User>('/users/me');
export const updateMe = (payload: Partial<User>) => put<User>('/users/me', payload);

// Profile
export const getMyProfile = () => get<Profile>('/profiles/me');
export const updateProfile = (payload: Partial<Profile>) => put<Profile>('/profiles/me', payload);
export const uploadAvatar = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return post<{ avatar_url: string }>('/profiles/avatar', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};
export const updateConsent = (payload: ConsentPayload) => post('/profiles/consent', payload);

// Discovery
export const discoveryUsers = (section: Section, params?: Record<string, unknown>) =>
  get<PaginatedResponse<DiscoveryItem>>(`/discovery/${section}`, { params });

export const discoveryUserDetail = (section: Section, userId: string) =>
  get<DiscoveryDetail>(`/discovery/${section}/users/${userId}`);

export const setPush = (section: Section, payload: PushPayload) =>
  post(`/discovery/${section}/push`, payload);

export const sendFeedback = (userId: string, payload: FeedbackPayload) =>
  post(`/matches/${userId}/feedback`, payload);

// Questionnaires
export const listQuestionnaires = () => get<Questionnaire[]>('/questionnaires');
export const getQuestionnaire = (slug: string) => get<Questionnaire>(`/questionnaires/${slug}`);
export const submitQuestionnaire = (slug: string, payload: QuestionnaireResponse) =>
  post<QuestionnaireResponse>(`/questionnaires/${slug}/responses`, payload);
export const getMyResponse = (slug: string) =>
  get<QuestionnaireResponse>(`/questionnaires/${slug}/responses/me`);

// Friends
export const sendFriendRequest = (payload: FriendRequestPayload) =>
  post<FriendRequest>('/friends/requests', payload);
export const listFriendRequests = (direction: 'received' | 'sent') =>
  get<PaginatedResponse<FriendRequest>>('/friends/requests', { params: { direction } });
export const acceptFriendRequest = (requestId: string) =>
  post<FriendRequest>(`/friends/requests/${requestId}/accept`);
export const rejectFriendRequest = (requestId: string) =>
  post<FriendRequest>(`/friends/requests/${requestId}/reject`);
export const listFriends = () => get<Friend[]>('/friends');
export const deleteFriend = (userId: string) => del(`/friends/${userId}`);

// Chat
export const listConversations = () =>
  get<PaginatedResponse<Conversation>>('/conversations');
export const getMessages = (conversationId: string, params?: { page?: number; limit?: number }) =>
  get<PaginatedResponse<Message>>(`/conversations/${conversationId}/messages`, { params });
export const sendMessage = (
  conversationId: string,
  content: string,
  messageType: 'text' | 'image' = 'text'
) => post<Message>(`/conversations/${conversationId}/messages`, { content, message_type: messageType });
export const uploadImageMessage = (conversationId: string, file: File) => {
  const form = new FormData();
  form.append('file', file);
  return post<Message>(`/conversations/${conversationId}/messages`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};
export const markMessageRead = (messageId: string) => post(`/messages/${messageId}/read`);

// Message board
export const listMessageBoard = (section: Section, params?: { owner_id?: string }) =>
  get<PaginatedResponse<MessageBoardItem>>(`/message-board/${section}`, { params });
export const postMessageBoard = (section: Section, payload: { owner_id: string; content: string }) =>
  post<MessageBoardItem>(`/message-board/${section}`, payload);

// Reports
export const createReport = (payload: {
  target_type: 'user' | 'message' | 'content';
  target_id: string;
  reason: string;
  description?: string;
}) => post('/reports', payload);

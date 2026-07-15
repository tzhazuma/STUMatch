import { apiClient } from './client';
import {
  AuthResponse,
  Conversation,
  DiscoveryResponse,
  DiscoveryUserDetail,
  Friend,
  FriendRequest,
  Message,
  Profile,
  Questionnaire,
  QuestionnaireDefinition,
  QuestionnaireResponse,
  Section,
  User,
} from '../types';

const unwrap = (res: any) => res.data?.data ?? res.data;

export const API = {
  auth: {
    login: (email: string, password: string): Promise<AuthResponse> =>
      apiClient
        .post('/auth/login', { email, phone: null, password })
        .then(unwrap),

    register: (payload: {
      email: string;
      code: string;
      password: string;
      nickname: string;
      school: string;
      referral_code?: string;
    }): Promise<AuthResponse> =>
      apiClient
        .post('/auth/register', { ...payload, phone: null })
        .then(unwrap),

    sendCode: (
      email: string,
      purpose: 'register' | 'login' | 'reset_password'
    ): Promise<{ ok: boolean; provider: string; target: string }> =>
      apiClient
        .post('/auth/send-verification-code', { email, phone: null, purpose })
        .then(unwrap),

    logout: (): Promise<any> => apiClient.post('/auth/logout').then(unwrap),
  },

  legal: {
    get: (doc: 'terms' | 'privacy'): Promise<{ title: string; content: string; updated_at: string }> =>
      apiClient.get(`/legal/${doc}`).then(unwrap),
  },

  me: {
    getMe: (): Promise<User> => apiClient.get('/users/me').then(unwrap),
    updateMe: (data: Partial<User>): Promise<User> =>
      apiClient.put('/users/me', data).then(unwrap),
    deleteMe: (): Promise<any> => apiClient.delete('/users/me').then(unwrap),
  },

  profile: {
    getMyProfile: (): Promise<Profile> =>
      apiClient.get('/profiles/me').then(unwrap),
    updateMyProfile: (data: Partial<Profile>): Promise<Profile> =>
      apiClient.put('/profiles/me', data).then(unwrap),
    uploadAvatar: (formData: FormData): Promise<{ avatar_url: string }> =>
      apiClient
        .post('/profiles/avatar', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        .then(unwrap),
    consent: (consentType: string, granted: boolean): Promise<any> =>
      apiClient.post('/profiles/consent', { consent_type: consentType, granted }).then(unwrap),
  },

  discovery: {
    discover: (
      section: Section,
      params: {
        q?: string;
        push?: boolean;
        page?: number;
        limit?: number;
      }
    ): Promise<DiscoveryResponse> =>
      apiClient.get(`/discovery/${section}`, { params }).then(unwrap),

    getUser: (section: Section, userId: string): Promise<DiscoveryUserDetail> =>
      apiClient.get(`/discovery/${section}/users/${userId}`).then(unwrap),

    setPush: (section: Section, enabled: boolean): Promise<any> =>
      apiClient.post(`/discovery/${section}/push`, { enabled }).then(unwrap),
  },

  questionnaires: {
    list: (): Promise<Questionnaire[]> =>
      apiClient.get('/questionnaires').then(unwrap),
    get: (slug: string): Promise<QuestionnaireDefinition> =>
      apiClient.get(`/questionnaires/${slug}`).then(unwrap),
    submit: (slug: string, answers: Record<string, string | string[]>): Promise<any> =>
      apiClient.post(`/questionnaires/${slug}/responses`, { answers }).then(unwrap),
    getMyResponses: (slug: string): Promise<QuestionnaireResponse> =>
      apiClient.get(`/questionnaires/${slug}/responses/me`).then(unwrap),
  },

  friends: {
    sendRequest: (toUserId: string, message: string): Promise<FriendRequest> =>
      apiClient
        .post('/friends/requests', { to_user_id: toUserId, message })
        .then(unwrap),

    getRequests: (direction: 'received' | 'sent'): Promise<FriendRequest[]> =>
      apiClient
        .get('/friends/requests', { params: { direction } })
        .then(unwrap),

    acceptRequest: (requestId: string): Promise<FriendRequest> =>
      apiClient.post(`/friends/requests/${requestId}/accept`).then(unwrap),

    rejectRequest: (requestId: string): Promise<FriendRequest> =>
      apiClient.post(`/friends/requests/${requestId}/reject`).then(unwrap),

    getFriends: (): Promise<Friend[]> =>
      apiClient.get('/friends').then(unwrap),

    deleteFriend: (userId: string): Promise<any> =>
      apiClient.delete(`/friends/${userId}`).then(unwrap),
  },

  chat: {
    getConversations: (): Promise<{ items: Conversation[] }> =>
      apiClient.get('/conversations').then(unwrap),

    getMessages: (
      conversationId: string,
      params?: { page?: number; limit?: number }
    ): Promise<{ items: Message[]; total: number; page: number; limit: number }> =>
      apiClient
        .get(`/conversations/${conversationId}/messages`, { params })
        .then(unwrap),

    sendMessage: (
      conversationId: string,
      content: string,
      messageType = 'text'
    ): Promise<Message> =>
      apiClient
        .post(`/conversations/${conversationId}/messages`, {
          content,
          message_type: messageType,
        })
        .then(unwrap),

    readMessage: (messageId: string): Promise<any> =>
      apiClient.post(`/messages/${messageId}/read`).then(unwrap),
  },

  referrals: {
    getMyCode: (): Promise<{ code: string; link: string; status: string }> => apiClient.get('/referrals/me').then(unwrap),
    applyCode: (code: string): Promise<any> => apiClient.post('/referrals/apply', { code }).then(unwrap),
    getStats: (): Promise<{ total_sent: number; total_used: number; total_rewarded: number }> => apiClient.get('/referrals/stats').then(unwrap),
  },
};

export type Section = 'academic' | 'daily' | 'dating';

export interface User {
  id: string;
  email: string;
  nickname: string;
  avatar_url?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Profile {
  id: string;
  user_id: string;
  nickname: string;
  avatar_url?: string;
  gender?: string;
  birth_date?: string;
  age?: number;
  education_level?: string;
  school?: string;
  major?: string;
  mbti?: string;
  interests?: string[];
  location?: string;
  bio?: string;
  research_direction?: string;
  dating_purpose?: string;
  family_status?: string;
  ideal_person?: string;
  is_verified_email?: boolean;
  is_verified_school?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface DiscoveryItem {
  user_id: string;
  nickname: string;
  avatar_url?: string;
  age?: number;
  education_level?: string;
  major?: string;
  interests?: string[];
  location?: string;
  match_score?: number;
  match_reason?: string;
}

export interface DiscoveryResponse {
  items: DiscoveryItem[];
  total: number;
  page: number;
  limit: number;
}

export interface DiscoveryUserDetail {
  user_id: string;
  nickname: string;
  avatar_url?: string;
  age?: number;
  gender?: string;
  education_level?: string;
  school?: string;
  major?: string;
  mbti?: string;
  interests?: string[];
  location?: string;
  bio?: string;
  research_direction?: string;
  dating_purpose?: string;
  family_status?: string;
  ideal_person?: string;
  match_score?: number;
  match_reason?: string;
}

export interface FriendRequest {
  id: string;
  requester_id: string;
  addressee_id: string;
  message?: string;
  status: 'pending' | 'accepted' | 'rejected';
  created_at: string;
  updated_at: string;
}

export interface Friend {
  user_id: string;
  nickname: string;
  avatar_url?: string;
  school?: string;
  major?: string;
}

export interface LastMessage {
  content: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  participant: User;
  last_message?: LastMessage;
  unread_count?: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_id: string;
  content: string;
  message_type: string;
  created_at: string;
  is_read?: boolean;
}

export interface Questionnaire {
  slug: string;
  title: string;
  description?: string;
  section?: Section | 'global';
}

export interface QuestionnaireQuestion {
  id: string;
  text: string;
  type: 'single_choice' | 'multiple_choice' | 'text';
  options?: { value: string; label: string }[];
  required?: boolean;
}

export interface QuestionnaireDefinition {
  slug: string;
  title: string;
  description?: string;
  questions: QuestionnaireQuestion[];
}

export interface QuestionnaireResponse {
  answers: Record<string, string | string[]>;
}

export interface ApiError {
  error?: string;
  message?: string;
}

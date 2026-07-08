export type Section = 'academic' | 'daily' | 'dating';

export interface User {
  id: string;
  email: string;
  nickname: string;
  avatar_url?: string;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthState extends Tokens {
  user: User | null;
  expires_at: number;
  isAuthenticated: boolean;
}

export interface Profile {
  id: string;
  user_id: string;
  nickname: string;
  avatar_url?: string;
  gender?: 'male' | 'female' | 'other';
  birth_date?: string;
  age?: number;
  education_level?: 'undergraduate' | 'master' | 'phd' | 'other';
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

export interface DiscoveryDetail {
  user_id: string;
  nickname: string;
  avatar_url?: string;
  section: Section;
  age?: number;
  education_level?: string;
  school?: string;
  major?: string;
  interests?: string[];
  location?: string;
  mbti?: string;
  bio?: string;
  research_direction?: string;
  dating_purpose?: string;
  family_status?: string;
  ideal_person?: string;
  match_score?: number;
  match_reason?: string;
}

export interface QuestionOption {
  value: string;
  label: string;
}

export type QuestionType = 'single_choice' | 'multiple_choice' | 'text' | 'rating' | 'tags';

export interface Question {
  id: string;
  text: string;
  type: QuestionType;
  required?: boolean;
  options?: QuestionOption[];
  max?: number;
  min?: number;
}

export interface Questionnaire {
  slug: string;
  title: string;
  description?: string;
  section?: Section | 'global';
  questions: Question[];
}

export interface QuestionnaireResponse {
  answers: Record<string, unknown>;
}

export interface FriendRequest {
  id: string;
  from_user_id: string;
  to_user_id: string;
  message?: string;
  status: 'pending' | 'accepted' | 'rejected';
  created_at: string;
  from_user?: { id: string; nickname: string; avatar_url?: string };
  to_user?: { id: string; nickname: string; avatar_url?: string };
}

export interface Friend {
  user_id: string;
  nickname: string;
  avatar_url?: string;
  conversation_id: string;
}

export interface Conversation {
  id: string;
  participant: { id: string; nickname: string; avatar_url?: string };
  last_message?: { content: string; created_at: string; message_type?: string };
  unread_count: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  sender_id: string;
  content: string;
  message_type: 'text' | 'image';
  created_at: string;
  is_read?: boolean;
}

export interface MessageBoardItem {
  id: string;
  owner_id: string;
  author_id: string;
  author?: { nickname: string; avatar_url?: string };
  content: string;
  created_at: string;
}

export interface ApiResponse<T> {
  data: T;
  error?: string | null;
  message?: string | null;
}

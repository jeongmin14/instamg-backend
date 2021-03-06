import json
import random
import subprocess
import time

from django.db.models  import Q
from pytz              import utc, timezone
from django.views      import View
from django.http       import JsonResponse, StreamingHttpResponse, HttpResponse
from django.db         import transaction
from datetime          import datetime

from decorators        import login_check
from users.models      import User, Follow
from .models           import Post, PostAttachFiles, Comment, Like, PostRead
from stories.models    import Story, StoryAttachFiles, StoryRead


class PostView(View):
    @login_check
    @transaction.atomic
    def post(self, request):
        try:
            data  = json.loads(request.POST['json'])
            user  = request.user
            video = ['m4v', 'avi','mpg','mp4', 'webm', 'MOV']
            image = ['jpg', 'gif', 'bmp', 'png', 'jpeg']

            Post.objects.create(
                user_id = user,
                content = data['content']
            )

            for path in request.FILES.getlist('path'):
                if str(path).split('.')[-1] in video:
                    file_type = "video"
                else:
                    file_type = "image"

                PostAttachFiles.objects.create(
                post_id        = Post.objects.last(),
                file_type      = file_type,
                path           = path,
                thumbnail_path = None
            )

                post_file      = str(PostAttachFiles.objects.last().path)
                video_path     = 'media/'+post_file
                thumbnail_path = 'media/thumbnail/'+post_file.split('/')[-1]

                subprocess.call(['ffmpeg', '-i', video_path, '-ss', '00:00:00.000', '-vframes', '1', '-y', thumbnail_path])
                
                post_file = PostAttachFiles.objects.last()
                post_file.thumbnail_path = thumbnail_path
                post_file.save()

            return JsonResponse({'message':'SUCCESS'}, status=201)
        except ValueError:
            return JsonResponse({'message':'VALUE_ERROR'}, status=400)
        except KeyError:
            return JsonResponse({'message':'KEY_ERROR'}, status=400)


# ????????? ?????? ??????
class PostReadView(View):
    @login_check
    def get(self, request):
        try:
            page           = int(request.GET.get("page", 1))
            PAGE_SIZE      = 10
            limit          = page * PAGE_SIZE
            offset         = limit - PAGE_SIZE
            user           = request.user
            following_list = [following.followed_user_id for following in Follow.objects.filter(follower_user_id=user)]
            posts          = Post.objects.filter(Q(user_id=user)|Q(user_id__in=following_list)).order_by('-created_at').prefetch_related('post_attach_files','likes')[offset:limit]
            post_list = [{ 
                    'post_id'        : post.id,
                    'user_id'        : post.user_id.id,
                    'user_account'   : post.user_id.account,
                    'content'        : post.content,
                    'profile_photo'  : "media/"+ str(post.user_id.thumbnail_path) if str(post.user_id.thumbnail_path) else None,
                    'like_count'     : post.like_count,
                    'is_liked'       : post.likes.filter(user_id=user, comment_id=None).exists(),
                    'total_comments' : post.comments.all().count(),
                    'comments'       : [{
                        'post_id'                    : comment.post_id.id,
                        'comment_id'                 : comment.id,
                        'content'                    : comment.content,
                        'comment_user_id'            : comment.user_id.id,
                        'comment_user_account'       : comment.user_id.account,
                        'comment_user_profile_photo' : "media/"+ str(comment.user_id.thumbnail_path) if str(comment.user_id.thumbnail_path) else None,
                        'created_at'                 : comment.created_at,
                        'is_liked'                   : comment.likes.exists()
                        }for comment in post.comments.all()[:2]],
                    'created_at'     : post.created_at.astimezone(timezone('Asia/Seoul')),
                    'file'           : [{
                                        'id'             : post_attach_file.id,
                                        'file_type'      : post_attach_file.file_type,
                                        'path'           : "media/"+str(post_attach_file.path),
                                        'thumbnail_path' : str(post_attach_file.thumbnail_path)
                                        }for post_attach_file in post.post_attach_files.all()]
                } for post in posts]
            return JsonResponse({'feed':post_list}, status=200)
        except ValueError:
            return JsonResponse({'message':'VALUE_ERROR'}, status=400)
        except IndexError:
            return JsonResponse({'message':'POST_DOES_NOT_EXIST'}, status=400)
            
                        
# ????????? ?????????
class PostStoryView(View):
    @login_check
    def get(self,request):
            try:
                following = Follow.objects.filter(follower_user_id=request.user)
                now       = utc.localize(datetime.utcnow())

                story_list = [[{
                'story_id'     : story.id,
                'created_at'   : story.created_at,
                'user_id'      : story.user_id.id,
                'user_account' : story.user_id.account,
                'profile_photo': "media/"+ str(story.user_id.thumbnail_path) if str(story.user_id.thumbnail_path) else None,
                } for story in Story.objects.filter(user_id=follow.followed_user_id).prefetch_related('story_attach_files') if 'days' not in str(now - story.created_at)]
                for follow in following if len(Story.objects.filter(user_id=follow.followed_user_id).prefetch_related('story_attach_files')) > 0 ]

                user_list = [{
                    'user_id'       : request.user.id,
                    'user_account'  : request.user.account,
                    'profile_photo' : "media/"+ str(request.user.thumbnail_path) if str(request.user.thumbnail_path) else None,
                }]
                story_list.append(user_list)
                return JsonResponse({'stories':story_list}, status=200)
            
            except KeyError:
                return JsonResponse({'message':'KEY_ERROR'}, status=400)


# ??????, ????????? ?????? #????????? ??????????????? ?????????
class PostCommentView(View):
    @login_check
    def get(self, request, post_id):
        try:
            post = Post.objects.filter(id=post_id).prefetch_related('comments')[0]
            comments_list=[{
                'post_id'                    : comment.post_id.id,
                'comment_id'                 : comment.id,
                'content'                    : comment.content,
                'comment_user_id'            : comment.user_id.id,
                'comment_user_account'       : comment.user_id.account,
                'comment_user_profile_photo' : "media/"+ str(comment.user_id.thumbnail_path) if str(comment.user_id.thumbnail_path) else None,
                'created_at'                 : comment.created_at,
                'is_liked'                   : comment.likes.exists(),
                'recomment'                  :[{
                                        'recomment_id'                 : recomment.id,
                                        'content'                      : recomment.content,
                                        'recomment_user_id'            : recomment.user_id.id,
                                        'recomment_user_account'       : recomment.user_id.account,
                                        'recomment_user_profile_photo' : "media/"+ str(recomment.user_id.thumbnail_path) if str(recomment.user_id.thumbnail_path) else None,
                                        'created_at'                   : recomment.created_at,
                                        'is_liked'                     : comment.likes.exists()
                } for recomment in Comment.objects.filter(comment_id=comment.id)]
            } for comment in post.comments.all() if comment.comment_id is None]
            return JsonResponse({'comment':comments_list}, status=200)

        except KeyError:
            return JsonResponse({'message':'KEY_ERROR'}, status=400)


# ????????? ??????
class PostModifyView(View):
    @login_check
    def post(self, request, post_id):
        try:
            data             = json.loads(request.POST['json'])
            post             = Post.objects.filter(id=post_id).prefetch_related('post_attach_files')
            post_attach_file = post[0].post_attach_files.all()
            video            = ['m4v', 'avi','mpg','mp4', 'webm', 'MOV']
            image            = ['jpg', 'gif', 'bmp', 'png', 'jpeg']

            post.update(
                content    = data['content'],
                created_at = datetime.now()
            )
                    
            for i in range(len(request.FILES.getlist('path'))):
                if str(request.FILES.getlist('path')[i]).split('.')[-1] in video:
                    file_type = "video"
                else:
                    file_type = "image"

                post_attach_file[i].file_type = file_type
                post_attach_file[i].path = request.FILES.getlist('path')[i]
                post_attach_file[i].save()

                if file_type == 'image':
                    post_attach_file[i].thumbnail_path = request.FILES.getlist('path')[i]
                else:
                    video_path     = 'media/'+str(post_attach_file[i].path)
                    thumbnail_path = 'media/thumbnail/'+str(post_attach_file[i].path).split('/')[-1]

                    subprocess.call(['ffmpeg', '-i', video_path, '-ss', '00:00:00.000', '-vframes', '1', '-y', thumbnail_path])
                    post_attach_file[i].thumbnail_path = 'media/thumbnail/' + str(post_attach_file[i].path).split('/')[-1]
                post_attach_file[i].save()

            return JsonResponse({'message':'SUCCESS'}, status=200)
        except KeyError:
            return JsonResponse({'message':'KEY_ERROR'}, status=400)
        except Post.DoesNotExist:
            return JsonResponse({'message':'POST_DOES_NOT_EXIST'}, status=400)


# ????????? ??????
class PostDeleteView(View):    
    @login_check
    def delete(self, request, post_id):
        try:
            post              = Post.objects.filter(id=post_id).prefetch_related('post_attach_files')[0]
            post_attach_files = post.post_attach_files.all()

            if post.user_id.id == request.user.id:
                post_attach_files.delete()
                post.delete()
                return JsonResponse({'message':'SUCCESS'}, status=200)
            else:
                return JsonResponse({'message':'NO_PERMISSION'}, status=403)
        except Post.DoesNotExist:
            return JsonResponse({"message":'POST_DOES_NOT_EXIST'}, status=400)


# ??????, ????????? ??????
class CommentView(View):
    @login_check
    def post(self, request, post_id):
        try:
            data = json.loads(request.body)
            
            if data.get('comment_id') is not None:
                comment_id = Comment.objects.get(id=data.get('comment_id'))
            else:
                comment_id = None

            Comment(
                post_id    = Post.objects.get(id=post_id),
                user_id    = request.user,
                content    = data['content'],
                comment_id = comment_id
            ).save()

            comment_last = Comment.objects.last()
            comment_data = {
                'comment_id'      : comment_last.id,
                'post_id'         : comment_last.post_id.id,
                'comment_content' : data['content'],
                'user_account'    : request.user.account,
                'user_profile'    : "media/"+ str(request.user.thumbnail_path) if str(request.user.thumbnail_path) else None
            }
            return HttpResponse(json.dumps({'message': 'SUCCESS', 'comment_data': comment_data}), status=201)
        except KeyError:
            return JsonResponse({'message':'KEY_ERROR'}, status=400)
        except Post.DoesNotExist :
            return JsonResponse({'message':'POST_DOES_NOT_EXIST'}, status=400)


# ??????, ????????? ??????
class CommentDeleteView(View):
    @login_check
    def post(self, request, comment_id):
        try:
            comment = Comment.objects.get(id=comment_id)

            comment_data = {
                'comment_id'      : comment.id,
                'post_id'         : comment.post_id.id,
                'comment_content' : comment.content,
                'user_account'    : request.user.account,
                'user_profile'    : "media/"+ str(request.user.thumbnail_path) if str(request.user.thumbnail_path) else None
            }
            if comment.user_id.id == request.user.id:
                comment.delete()
                return HttpResponse(json.dumps({'message': 'SUCCESS', 'comment_data': comment_data}), status=200)
            return JsonResponse({'message':'NO_PERMISSION'}, status=403)
        except Comment.DoesNotExist:
            return JsonResponse({'message':'COMMENT_DOES_NOT_EXIST.'}, status=400)


# ??????, ????????? ??????
class CommentModifyView(View):
    @login_check
    def post(self, request, post_id, comment_id):
        try:
            data    = json.loads(request.body)
            comment = Comment.objects.filter(id=comment_id)
            comment.update(
                content    = data['content'],
                created_at = datetime.now()
            )

            return JsonResponse({'message':'SUCCESS'}, status=201)
        except KeyError:
            return JsonResponse({'message':'KEY_ERROR'}, status=400)
            
        except Comment.DoesNotExist:
            return JsonResponse({'message':'COMMENT_DOES_NOT_EXIST'}, status=400)


# ??????, ????????? ?????????
class CommentLikeView(View):
    @login_check
    def post(self, request, comment_id):
        try:
            comment = Comment.objects.get(id=comment_id)

            if Like.objects.filter(comment_id=comment.id, user_id=request.user).exists():
                like = Like.objects.filter(comment_id=comment.id, user_id=request.user)
                like.delete()
                return JsonResponse({'message':'SUCCESS'}, status=200)

            Like.objects.create(
                comment_id = comment,
                user_id    = request.user
            )
            return JsonResponse({'message':'SUCCESS'}, status=201)

        except KeyError:
            return JsonResponse({'message':'KEY_ERROR'}, status=400)
        except Comment.DoesNotExist :
            return JsonResponse({'message':'COMMENT_DOES_NOT_EXIST'}, status=400)


# ????????? ????????? ??????
class PostLikeView(View):
    @login_check
    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            
            if Like.objects.filter(post_id=post.id, user_id=request.user).exists():
                like = Like.objects.filter(post_id=post.id, user_id=request.user)
                like.delete()
                post.like_count -= 1
                post.save()
                return JsonResponse({'message':'UNLIKE_SUCCESS'}, status=200)

            Like.objects.create(
                post_id = post,
                user_id = request.user
            )
            post.like_count += 1
            post.save()
            return JsonResponse({'message':'LIKE_SUCCESS'}, status=201)

        except KeyError:
            return JsonResponse({'message':'KEY_ERROR'}, status=400)
        except Post.DoesNotExist :
            return JsonResponse({'message':'POST_DOES_NOT_EXIST'}, status=400)


# ???????????? ????????? ?????? ??????
class ProfileView(View):
    @login_check
    def get(self, request, user_id):
        try:
            login_user    = request.user
            user          = User.objects.get(id = user_id)
            now           = utc.localize(datetime.utcnow())
            stories       = user.story_set.all()
            created_story = [story.created_at for story in stories if 'days' not in str(now - story.created_at)]
            result        = {
                "id"              : user.id,
                "account"         : user.account,
                "profile_photo"   : "media/"+str(user.thumbnail_path) if str(user.thumbnail_path) else None,
                "is_myprofile"    : True if login_user.id==user_id else False,
                "is_following"    : Follow.objects.filter(followed_user_id_id=user, follower_user_id=login_user).exists(),
                "post_count"      : user.post_set.count(),
                "follower_count"  : Follow.objects.filter(followed_user_id_id=user).count(),
                "following_count" : Follow.objects.filter(follower_user_id_id=user).count(),
                "profile_message" : user.profile_message,
                "living"          : random.choice([True, False]),
                "today_live"      : True if len(created_story) > 0  else False, #24????????? ????????? ???????????? ??? True
            }
            return JsonResponse({"profile" : result}, status=200)
        except KeyError:
            return JsonResponse({"message" : "KEY_ERROR"}, status=400)
        

# ???????????? ?????????(9??????)??????
class ProfileFeedView(View):
    def get(self, request, user_id):
        try:
            user       = User.objects.get(id = user_id)
            like       = Like.objects.filter(comment_id_id=None)
            page       = int(request.GET.get("page", 1))
            PAGE_SIZE  = 9
            limit      = page * PAGE_SIZE
            offset     = limit - PAGE_SIZE

            post_list  = [
                {
                    "post_id"        : post.id,
                    "content"        : post.content,
                    "created_at"     : post.created_at.astimezone(timezone('Asia/Seoul')),
                    "like_count"     : post.like_count,
                    "comments_count" : Comment.objects.filter(post_id_id=post.id).count(),
                    "is_multiple"    : False if post.post_attach_files.count()==1 else True,
                    "file"           : [{
                        "id"             : post_attach_file.id,
                        "file_type"      : post_attach_file.file_type,
                        "view_count"     : post_attach_file.view_count,
                        "thumbnail_path" : str(post_attach_file.thumbnail_path)
                    }for post_attach_file in post.post_attach_files.all()],
                }for post in user.post_set.all().order_by('-created_at').prefetch_related('post_attach_files')][offset:limit]
            return JsonResponse({"post_list" : post_list}, status = 200)
        except KeyError:
            return JsonResponse({"message" : "KEY_ERROR"}, status=400)


# post ?????? ??????(?????????)
class PostDetailView(View):
    @login_check
    def get(self, request, post_id): 
        try:
            login_user    = request.user
            post          = Post.objects.filter(id=post_id).prefetch_related('post_attach_files', 'comments')[0]
            now           = utc.localize(datetime.utcnow())
            stories       = post.user_id.story_set.all()
            created_story = [story.created_at for story in stories if 'days' not in str(now - story.created_at)]
            post          = { 
                    'post_id'            : post.id,  
                    'user_id'            : post.user_id.id,
                    'account'            : post.user_id.account,
                    'profile_photo'      : 'media/'+ str(post.user_id.thumbnail_path) if str(post.user_id.thumbnail_path) else None,
                    'content'            : post.content,
                    'like_count'         : post.like_count,
                    'created_at'         : post.created_at.astimezone(timezone('Asia/Seoul')),
                    'today_live'         : True if len(created_story) > 0  else False,
                    'isowner_following'  : Follow.objects.filter(followed_user_id_id=post.user_id.id, follower_user_id=login_user).exists(),
                    'is_liked'           : Like.objects.filter(user_id_id=login_user, post_id=post.id).exists(),
                    'login_user_account' : login_user.account,
                    'comments'           : [{
                                        'comment_id'                 : comment.id,
                                        'content'                    : comment.content,
                                        'user_id'                    : comment.user_id.id,
                                        'account'                    : comment.user_id.account,
                                        'profile_photo'              : 'media/'+ str(comment.user_id.thumbnail_path) if str(comment.user_id.thumbnail_path) else None,
                                        'created_at'                 : comment.created_at.astimezone(timezone('Asia/Seoul')),
                                        'like_count'                 : Like.objects.filter(comment_id=comment.id).count(),
                                        'is_liked'                   : comment.likes.exists(),
                                        'recomment'                  :[{
                                            'comment_id'                   : comment.id,
                                            'recomment_id'                 : recomment.id,
                                            'content'                      : recomment.content,
                                            'user_id'                      : recomment.user_id.id,
                                            'account'                      : recomment.user_id.account,
                                            'profile_photo'                : 'media/'+ str(recomment.user_id.thumbnail_path) if str(recomment.user_id.thumbnail_path) else None,
                                            'created_at'                   : recomment.created_at.astimezone(timezone('Asia/Seoul')),
                                            'like_count'                   : Like.objects.filter(comment_id=recomment.id).count(),
                                            'is_liked'                     : recomment.likes.exists()
                                        } for recomment in Comment.objects.filter(comment_id=comment.id)]
            } for comment in post.comments.filter(comment_id=None)],
                    'file'              :[{
                                    'id'             : post_attach_file.id,
                                    'file_type'      : post_attach_file.file_type,
                                    "view_count"     : post_attach_file.view_count,
                                    'path'           : 'media/'+str(post_attach_file.path),
                                    'thumbnail_path' : str(post_attach_file.thumbnail_path)
                    }for post_attach_file in post.post_attach_files.all()]
            }
            return JsonResponse({'post':post}, status=200)
        except ValueError:
            return JsonResponse({'message':'VALUE_ERROR'}, status=400)
        except IndexError:
            return JsonResponse({'message':'POST_DOES_NOT_EXIST'}, status=400)


# GoToPost ??? ??????????????? 6?????? ??????
class GoToPostView(View):
    def get(self, request, user_id, post_id):
        try:
            user = User.objects.get(id = user_id)
    
            post_list = [{
                "post_id"        : post.id,
                "content"        : post.content,
                "created_at"     : post.created_at.astimezone(timezone('Asia/Seoul')),
                "like_count"     : post.like_count,
                "comments_count" : Comment.objects.filter(post_id_id=post.id).count(),
                "is_multiple"    : False if post.post_attach_files.count()==1 else True,
                "files" : [{
                    "id"             : post_attach_file.id, 
                    "file_type"      : post_attach_file.file_type,
                    "view_count"     : post_attach_file.view_count,
                    "thumbnail_path" : str(post_attach_file.thumbnail_path)
                }for post_attach_file in post.post_attach_files.all()[:1]],
            }for post in user.post_set.exclude(id=post_id).order_by('-created_at').prefetch_related('post_attach_files')[0:6]]
            return JsonResponse({"go_to_post" : post_list}, status=200)
        except KeyError:
            return JsonResponse({"message" : "KEY_ERROR"}, status=400)


# ?????????????????? ????????? view_count ??????
class Viewcount(View):
    @login_check
    def post(self, request, postattachfiles_id):
        try:
            post = PostAttachFiles.objects.get(id=postattachfiles_id)
    
            if post.file_type=='video':
                post.view_count += 1
                post.save()
                return JsonResponse({'message':'SUCCESS'}, status=201)
            return JsonResponse({'message':'NOT_VIDEO_FILE'})
        except KeyError:
            return JsonResponse({'message':'KEY_ERROR'}, status=400)        
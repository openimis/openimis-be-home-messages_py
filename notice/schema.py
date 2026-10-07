import graphene
from core.schema import OrderedDjangoFilterConnectionField
from core import filter_validity
from django.core.exceptions import PermissionDenied
from .gql_queries import NoticeGQLType, NoticeAttachmentGQLType
from .gql_mutations import (
    CreateNoticeMutation,
    UpdateNoticeMutation,
    DeleteNoticeMutation,
    ToggleNoticeStatusMutation,
    CreateNoticeAttachmentMutation,
    UpdateNoticeAttachmentMutation,
    DeleteNoticeAttachmentMutation,
)
from .models import Notice, NoticeAttachment, NoticeMutation
from .apps import NoticeConfig
from core.schema import signal_mutation_module_validate




class Query(graphene.ObjectType):
    notices = OrderedDjangoFilterConnectionField(
        NoticeGQLType,
        show_history=graphene.Boolean(required=False),
        showHistory=graphene.Boolean(required=False),
        fetch_all=graphene.Boolean(required=False),
        orderBy=graphene.List(of_type=graphene.String),
    )
    notice_attachments = OrderedDjangoFilterConnectionField(
            NoticeAttachmentGQLType,
            orderBy=graphene.List(of_type=graphene.String),
        ) 



    def resolve_notices(self, info, **kwargs):
        if not info.context.user.has_perms(NoticeConfig.gql_query_notices_perms):
            raise PermissionDenied("Unauthorized")
        show_history = kwargs.get("showHistory", False) or kwargs.get("show_history", False)
        queryset = Notice.objects.all()
        if not show_history and not kwargs.get("legacy_id") and not kwargs.get("legacyId"):
            queryset = queryset.filter(*filter_validity())
        return queryset

    def resolve_notice_attachments(self, info, **kwargs):
        if not info.context.user.has_perms(NoticeConfig.gql_query_notices_perms):
            raise PermissionDenied("Unauthorized")
        queryset = NoticeAttachment.objects.filter(*filter_validity())
        if "notice_Uuid" in kwargs:
            queryset = queryset.filter(notice__uuid=kwargs["notice_Uuid"])
        return queryset
    

class Mutation(graphene.ObjectType):
    create_notice = CreateNoticeMutation.Field()
    update_notice = UpdateNoticeMutation.Field()
    delete_notice = DeleteNoticeMutation.Field()
    toggle_notice_status = ToggleNoticeStatusMutation.Field()
    create_notice_attachment = CreateNoticeAttachmentMutation.Field()
    update_notice_attachment = UpdateNoticeAttachmentMutation.Field()
    delete_notice_attachment = DeleteNoticeAttachmentMutation.Field()


def on_notice_mutation(**kwargs):
    uuids = kwargs["data"].get("uuids", [])
    if not uuids:
        uuid = kwargs["data"].get("uuid", None)  # For single-notice mutations
        uuids = [uuid] if uuid else []
    if not uuids:
        return []  # No notices impacted

    impacted_notices = Notice.objects.filter(uuid__in=uuids).all()
    for notice in impacted_notices:
        NoticeMutation.objects.create(
            notice=notice,
            mutation_id=kwargs["mutation_log_id"]
        )
    
    return []  # Return empty list (consistent with signal expectations)

def bind_signals():
    signal_mutation_module_validate["notice"].connect(on_notice_mutation)
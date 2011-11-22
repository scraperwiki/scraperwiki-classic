from django.db import models
from django.contrib.auth.models import User


PLAN_TYPES = (
    ('individual', 'Individual'),
    ('corporate', 'Corporate'),    
)

# Multiple instances per user are now allowed
class Vault(models.Model):
    
    user = models.ForeignKey(User, related_name='vaults')
    name = models.CharField(max_length=64, blank=True)    
    
    created_at = models.DateTimeField(auto_now_add=True)
    plan = models.CharField(max_length=32, choices=PLAN_TYPES)    

    # A list of the members who can access this vault.  This is 
    # distinct from the owner (self.user) of the vault.
    members = models.ManyToManyField(User, related_name='vault_membership')

    def code_objects(self):
        from codewiki.models import UserCodeRole, Code                
        return Code.objects.filter(vault=self).exclude(privacy_status='deleted')

    def add_user_rights(self, user ):
        """
        A new user has been added to the vault, make sure they can access all of 
        the code objects.
        """
        from codewiki.models import UserCodeRole, Code        
        role = 'editor'
        if user == self.user:
            role = 'owner'
        for code_object in self.code_objects().all():
            UserCodeRole(code=code_object, user=user,role='editor').save()
            
        
    def remove_user_rights(self, user ):
        """
        A user has been removed from the vault, make sure they can access none of 
        the code objects.
        """
        from codewiki.models import UserCodeRole, Code                
        for code_object in self.code_objects().all():
            UserCodeRole.objects.filter(code=code_object, user=user).all().delete()
        
        
    def update_access_rights(self):
        """
        A code_object has been added to the vault, make sure the UserCodeRoles
        are correct.
        """
        from codewiki.models import UserCodeRole, Code                
        for code_object in self.code_objects().all():
            UserCodeRole.objects.filter(code=code_object).all().delete()
            users = list(self.members.all())
            try:
                users.remove( self.user )
            except ValueError:
                pass
                
            UserCodeRole(code=code_object, user=self.user,role='owner').save()
            for u in users:
                UserCodeRole(code=code_object, user=u,role='editor').save()



    def __unicode__(self):
        return "%s' %s vault (created on %s)" % (self.user.username, self.plan, self.name)

    class Meta:
        app_label = 'codewiki'
        ordering = ['-name']


